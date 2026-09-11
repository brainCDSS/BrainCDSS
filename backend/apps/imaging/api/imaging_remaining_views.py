import os
import uuid

from django.core.paginator import (
    EmptyPage,
    Paginator,
)
from django.db import transaction
from django.utils import timezone

from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.errors import ContractAPIException
from apps.audit.services.audit_event import record_audit_event
from apps.common.models import OutboxEvent
from apps.imaging.api.imaging_remaining_auth import (
    ImagingAdminRetryPermission,
    ImagingNursePermission,
    ImagingServiceJWTAuthentication,
    RequiredImagingServiceScopePermission,
    ViewerDicomReadPermission,
    ViewerJWTAuthentication,
)
from apps.imaging.api.imaging_remaining_serializers import (
    DicomQidoQuerySerializer,
    DicomStowResponseSerializer,
    DicomStowSerializer,
    ImagingStatusEventResponseSerializer,
    ImagingStatusEventSerializer,
    ReconciliationListSerializer,
    ReconciliationQuerySerializer,
    ReconciliationResolveResponseSerializer,
    ReconciliationResolveSerializer,
    ResyncRequestSerializer,
    ResyncResponseSerializer,
    StableStudyEventSerializer,
    StableStudyResponseSerializer,
    TransferRetryResponseSerializer,
    TransferRetrySerializer,
)
from apps.imaging.models import (
    ImagingOrder,
    ImagingReconciliationTask,
    ImagingStudy,
)
from apps.imaging.services.imaging_remaining import (
    _integration,
    _outbox,
    apply_orthanc_snapshot,
    apply_status_event,
    register_dicom_stow,
    resolve_reconciliation,
    retry_transfer_job,
)
from apps.imaging.services.orthanc_client import (
    OrthancUnavailable,
    fetch_study_snapshot,
    qido_series,
)
from apps.integrations.models import IntegrationTransaction


def _page_url(
    request,
    page_number,
):
    if page_number is None:
        return None

    query = request.GET.copy()
    query["page"] = page_number

    return request.build_absolute_uri(
        f"{request.path}?{query.urlencode()}"
    )


class ImagingStudyResyncView(APIView):
    permission_classes = (
        ImagingAdminRetryPermission,
    )

    @extend_schema(
        operation_id="api_img_008",
        summary="Orthanc Study 재동기화",
        request=ResyncRequestSerializer,
        responses={
            202: ResyncResponseSerializer,
        },
        tags=["imaging"],
    )
    def post(
        self,
        request,
        study_id,
    ):
        serializer = ResyncRequestSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        study = (
            ImagingStudy.objects
            .filter(pk=study_id)
            .first()
        )

        if study is None:
            raise ContractAPIException(
                "IMAGING_STUDY_NOT_FOUND",
                "Imaging study not found.",
                404,
            )

        if not study.orthanc_study:
            raise ContractAPIException(
                "ORTHANC_STUDY_NOT_LINKED",
                "orthanc_study_id is missing.",
                409,
            )

        active = (
            IntegrationTransaction.objects
            .filter(
                message_type=
                    "ORTHANC_STUDY_RESYNC",
                external_message=
                    str(study.id),
                status__in=[
                    "PENDING",
                    "PROCESSING",
                ],
            )
            .exists()
        )

        if active:
            raise ContractAPIException(
                "RESYNC_ALREADY_RUNNING",
                "Study resync is already running.",
                409,
            )

        trace = getattr(
            request,
            "request_id",
            uuid.uuid4(),
        )

        txn = _integration(
            direction="OUTBOUND",
            source="BrainOn",
            target="Orthanc",
            message_type=
                "ORTHANC_STUDY_RESYNC",
            external_message=
                study.id,
            trace=trace,
            status="PROCESSING",
        )

        try:
            snapshot = fetch_study_snapshot(
                study.orthanc_study
            )

        except OrthancUnavailable as exc:
            txn.status = "FAILED"
            txn.error_code = (
                "ORTHANC_UNAVAILABLE"
            )
            txn.completed_at = timezone.now()
            txn.save(
                update_fields=[
                    "status",
                    "error_code",
                    "completed_at",
                ]
            )

            raise ContractAPIException(
                "ORTHANC_UNAVAILABLE",
                "Orthanc is unavailable.",
                503,
            ) from exc

        with transaction.atomic():
            locked = (
                ImagingStudy.objects
                .select_for_update()
                .get(pk=study.id)
            )

            study = apply_orthanc_snapshot(
                snapshot=snapshot,
                existing_study=locked,
            )

            txn.status = "SUCCESS"
            txn.completed_at = timezone.now()
            txn.save(
                update_fields=[
                    "status",
                    "completed_at",
                ]
            )

            _outbox(
                "imaging.study.resynced.v1",
                "ImagingStudy",
                study.id,
                {
                    "study_id":
                        str(study.id),
                    "status":
                        study.status,
                    "force":
                        serializer.validated_data[
                            "force"
                        ],
                },
            )

            record_audit_event(
                source_service="imaging",
                action="RESYNC_IMAGING_STUDY",
                resource_type="ImagingStudy",
                resource_id=study.id,
                patient_id=study.patient_id,
                outcome="SUCCESS",
                request=request,
                reason=
                    serializer.validated_data[
                        "reason"
                    ],
            )

        return Response(
            ResyncResponseSerializer({
                "study_id": study.id,
                "status": study.status,
                "series_count":
                    study.series_count,
                "instance_count":
                    study.instance_count,
                "last_synced_at":
                    study.last_synced_at,
            }).data,
            status=202,
        )


class OrthancStableStudyView(APIView):
    authentication_classes = (
        ImagingServiceJWTAuthentication,
    )

    permission_classes = (
        RequiredImagingServiceScopePermission,
    )

    required_service_scope = (
        "orthanc.event.write"
    )

    @extend_schema(
        operation_id="api_img_011",
        summary="Orthanc Stable Study 이벤트 수신",
        request=StableStudyEventSerializer,
        responses={
            202:
                StableStudyResponseSerializer,
        },
        tags=["imaging"],
    )
    def post(self, request):
        serializer = StableStudyEventSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data
        event_id = str(data["event_id"])

        existing_txn = (
            IntegrationTransaction.objects
            .filter(
                message_type=
                    "ORTHANC_STABLE_STUDY",
                external_message=event_id,
                status="SUCCESS",
            )
            .first()
        )

        if existing_txn:
            study = (
                ImagingStudy.objects
                .filter(
                    orthanc_study=
                        data[
                            "orthanc_study_id"
                        ]
                )
                .first()
            )

            if study:
                return Response(
                    StableStudyResponseSerializer({
                        "study_id":
                            study.id,
                        "status":
                            study.status,
                        "series_count":
                            study.series_count,
                        "instance_count":
                            study.instance_count,
                        "idempotent":
                            True,
                    }).data,
                    status=202,
                )

        allowed_origin = os.getenv(
            "ORTHANC_ALLOWED_ORIGIN"
        )

        supplied_origin = (
            request.headers.get(
                "X-Orthanc-Origin"
            )
        )

        if (
            allowed_origin
            and supplied_origin
            != allowed_origin
        ):
            raise ContractAPIException(
                "ORTHANC_ORIGIN_FORBIDDEN",
                "Orthanc origin is not allowed.",
                403,
            )

        principal = request.user

        txn = _integration(
            direction="INBOUND",
            source=
                principal.service_name,
            target="BrainOn",
            message_type=
                "ORTHANC_STABLE_STUDY",
            external_message=event_id,
            trace=getattr(
                request,
                "request_id",
                event_id,
            ),
            status="PROCESSING",
        )

        try:
            snapshot = fetch_study_snapshot(
                data[
                    "orthanc_study_id"
                ]
            )

        except OrthancUnavailable as exc:
            txn.status = "FAILED"
            txn.error_code = (
                "ORTHANC_UNAVAILABLE"
            )
            txn.completed_at = timezone.now()
            txn.save(
                update_fields=[
                    "status",
                    "error_code",
                    "completed_at",
                ]
            )

            raise ContractAPIException(
                "ORTHANC_UNAVAILABLE",
                "Orthanc is unavailable.",
                503,
            ) from exc

        with transaction.atomic():
            study = apply_orthanc_snapshot(
                snapshot=snapshot
            )

            txn.status = "SUCCESS"
            txn.completed_at = timezone.now()
            txn.save(
                update_fields=[
                    "status",
                    "completed_at",
                ]
            )

            event_type = {
                "AVAILABLE":
                    "imaging.study.available.v1",
                "UNMATCHED":
                    "imaging.study.unmatched.v1",
                "INCOMPLETE":
                    "imaging.study.incomplete.v1",
            }.get(
                study.status,
                "imaging.study.sync_failed.v1",
            )

            _outbox(
                event_type,
                "ImagingStudy",
                study.id,
                {
                    "study_id":
                        str(study.id),
                    "status":
                        study.status,
                },
            )

        return Response(
            StableStudyResponseSerializer({
                "study_id":
                    study.id,
                "status":
                    study.status,
                "series_count":
                    study.series_count,
                "instance_count":
                    study.instance_count,
                "idempotent":
                    False,
            }).data,
            status=202,
        )


class ImagingOrderStatusEventView(APIView):
    authentication_classes = (
        ImagingServiceJWTAuthentication,
    )

    permission_classes = (
        RequiredImagingServiceScopePermission,
    )

    required_service_scope = (
        "imaging.status.write"
    )

    @extend_schema(
        operation_id="api_img_016",
        summary="영상검사 상태 이벤트 수신",
        request=ImagingStatusEventSerializer,
        responses={
            202:
                ImagingStatusEventResponseSerializer,
        },
        tags=["imaging"],
    )
    def post(
        self,
        request,
        order_id,
    ):
        serializer = ImagingStatusEventSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        key = request.headers.get(
            "Idempotency-Key"
        )

        if not key:
            raise ContractAPIException(
                "INVALID_STATUS_EVENT",
                "Idempotency-Key header is required.",
                400,
            )

        try:
            order, study, duplicate = (
                apply_status_event(
                    order_id=order_id,
                    data=
                        serializer.validated_data,
                    idempotency_key=key,
                    service_name=
                        request.user.service_name,
                )
            )

        except ValueError as exc:
            code = str(exc)

            if code == (
                "INVALID_STATUS_TRANSITION"
            ):
                raise ContractAPIException(
                    code,
                    "Invalid imaging order status transition.",
                    409,
                ) from exc

            if code == (
                "STUDY_ORDER_MISMATCH"
            ):
                raise ContractAPIException(
                    code,
                    "Study does not match order/patient.",
                    422,
                ) from exc

            if code == (
                "COMPLETED_STUDY_REQUIRED"
            ):
                raise ContractAPIException(
                    "INVALID_STATUS_EVENT",
                    (
                        "COMPLETED requires "
                        "study_instance_uid or "
                        "an existing linked study."
                    ),
                    400,
                ) from exc

            raise

        if order is None:
            raise ContractAPIException(
                "ORDER_NOT_FOUND",
                "Imaging order not found.",
                404,
            )

        from apps.imaging.models import (
            ImagingOrderStatusHistory,
        )

        history_query = (
            ImagingOrderStatusHistory.objects
            .filter(
                imaging_order=order,
                status=
                    serializer.validated_data[
                        "status"
                    ],
            )
        )

        if duplicate:
            history_query = (
                history_query.filter(
                    occurred_at=
                        serializer.validated_data[
                            "occurred_at"
                        ]
                )
            )

        latest = (
            history_query
            .order_by(
                "-occurred_at",
                "-id",
            )
            .first()
        )

        previous = (
            latest.previous_status
            if latest
            else order.status
        )

        return Response(
            ImagingStatusEventResponseSerializer({
                "order_id":
                    order.id,
                "previous_status":
                    previous,
                "status":
                    order.status,
                "occurred_at":
                    serializer.validated_data[
                        "occurred_at"
                    ],
                "study_id": (
                    study.id
                    if study
                    else None
                ),
                "idempotent":
                    duplicate,
            }).data,
            status=202,
        )


class ImagingReconciliationListView(
    APIView
):
    permission_classes = (
        ImagingNursePermission,
    )

    @extend_schema(
        operation_id="api_img_017",
        summary="영상 매핑 불일치 Task 목록",
        parameters=[
            ReconciliationQuerySerializer,
        ],
        responses={
            200:
                ReconciliationListSerializer,
        },
        tags=["imaging"],
    )
    def get(self, request):
        serializer = (
            ReconciliationQuerySerializer(
                data=request.query_params
            )
        )
        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data

        queryset = (
            ImagingReconciliationTask.objects
            .select_related(
                "study",
                "imaging_order",
            )
            .filter(
                status=data["status"]
            )
        )

        if data.get("issue_code"):
            queryset = queryset.filter(
                issue_code=
                    data["issue_code"]
            )

        if data.get("study_id"):
            queryset = queryset.filter(
                study_id=
                    data["study_id"]
            )

        queryset = queryset.order_by(
            "-detected_at",
            "-id",
        )

        paginator = Paginator(
            queryset,
            data["page_size"],
        )

        try:
            page = paginator.page(
                data["page"]
            )
        except EmptyPage as exc:
            raise ContractAPIException(
                "INVALID_QUERY_PARAMETER",
                "Requested page does not exist.",
                400,
            ) from exc

        results = []

        for task in page.object_list:
            candidates = []

            if task.study.accession_number:
                candidate_orders = (
                    ImagingOrder.objects
                    .select_related("patient")
                    .filter(
                        accession_number=
                            task.study
                            .accession_number
                    )[:10]
                )

                candidates = [
                    {
                        "imaging_order_id":
                            order.id,
                        "patient_id":
                            order.patient_id,
                        "patient_no":
                            order.patient.patient_no,
                        "patient_name":
                            order.patient.name,
                        "accession_number":
                            order.accession_number,
                    }
                    for order
                    in candidate_orders
                ]

            results.append({
                "task_id": task.id,
                "study_id":
                    task.study_id,
                "imaging_order_id":
                    task.imaging_order_id,
                "issue_code":
                    task.issue_code,
                "status":
                    task.status,
                "detected_at":
                    task.detected_at,
                "candidates":
                    candidates,
            })

        return Response(
            ReconciliationListSerializer({
                "count":
                    paginator.count,
                "next":
                    _page_url(
                        request,
                        (
                            page.next_page_number()
                            if page.has_next()
                            else None
                        ),
                    ),
                "previous":
                    _page_url(
                        request,
                        (
                            page.previous_page_number()
                            if page.has_previous()
                            else None
                        ),
                    ),
                "results":
                    results,
            }).data
        )


class ImagingReconciliationResolveView(
    APIView
):
    permission_classes = (
        ImagingNursePermission,
    )

    @extend_schema(
        operation_id="api_img_018",
        summary="영상 매핑 불일치 Task 해결",
        request=
            ReconciliationResolveSerializer,
        responses={
            200:
                ReconciliationResolveResponseSerializer,
        },
        tags=["imaging"],
    )
    def post(
        self,
        request,
        task_id,
    ):
        serializer = (
            ReconciliationResolveSerializer(
                data=request.data
            )
        )
        serializer.is_valid(
            raise_exception=True
        )

        try:
            task = resolve_reconciliation(
                task_id=task_id,
                data=
                    serializer.validated_data,
                user=request.user,
                request=request,
            )

        except ValueError as exc:
            code = str(exc)

            if code == "TASK_INVALID_STATE":
                raise ContractAPIException(
                    code,
                    "Task is not resolvable.",
                    409,
                ) from exc

            if code == (
                "RECONCILIATION_MISMATCH"
            ):
                raise ContractAPIException(
                    code,
                    (
                        "Patient/order/study "
                        "mapping does not match."
                    ),
                    422,
                ) from exc

            raise

        if task is None:
            raise ContractAPIException(
                "TASK_NOT_FOUND",
                "Reconciliation task not found.",
                404,
            )

        return Response(
            ReconciliationResolveResponseSerializer({
                "task_id":
                    task.id,
                "status":
                    task.status,
                "resolved_patient_id":
                    task.resolved_patient_id,
                "resolved_order_id":
                    task.imaging_order_id,
                "resolved_by":
                    task.resolved_by_id,
                "resolved_at":
                    task.resolved_at,
                "study_status":
                    task.study.status,
            }).data
        )


class DicomTransferRetryView(APIView):
    permission_classes = (
        ImagingAdminRetryPermission,
    )

    @extend_schema(
        operation_id="api_img_019",
        summary="실패 DICOM 전송 재시도",
        request=TransferRetrySerializer,
        responses={
            202:
                TransferRetryResponseSerializer,
        },
        tags=["imaging"],
    )
    def post(
        self,
        request,
        job_id,
    ):
        serializer = TransferRetrySerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        try:
            job = retry_transfer_job(
                job_id=job_id,
                reason=
                    serializer.validated_data[
                        "reason"
                    ],
                user=request.user,
                request=request,
            )

        except ValueError as exc:
            if (
                str(exc)
                == "TRANSFER_JOB_NOT_RETRYABLE"
            ):
                raise ContractAPIException(
                    "TRANSFER_JOB_NOT_RETRYABLE",
                    "Transfer job is not FAILED.",
                    409,
                ) from exc

            raise

        if job is None:
            raise ContractAPIException(
                "TRANSFER_JOB_NOT_FOUND",
                "Transfer job not found.",
                404,
            )

        return Response(
            TransferRetryResponseSerializer({
                "job_id":
                    job.id,
                "status":
                    job.status,
                "attempt_count":
                    job.attempt_count,
                "trace_id":
                    job.trace,
            }).data,
            status=202,
        )


class DicomQidoSeriesView(APIView):
    authentication_classes = (
        ViewerJWTAuthentication,
    )

    permission_classes = (
        ViewerDicomReadPermission,
    )

    @extend_schema(
        operation_id="api_dicom_001",
        summary="OHIF DICOM Series QIDO 조회",
        parameters=[
            DicomQidoQuerySerializer,
        ],
        responses={
            200: dict,
        },
        tags=["dicom"],
    )
    def get(
        self,
        request,
        study_instance_uid,
    ):
        query = DicomQidoQuerySerializer(
            data=request.query_params
        )
        query.is_valid(
            raise_exception=True
        )

        claims = request.viewer_claims

        if (
            claims.get(
                "study_instance_uid"
            )
            != study_instance_uid
        ):
            raise ContractAPIException(
                "DICOM_SCOPE_FORBIDDEN",
                (
                    "Viewer token is bound "
                    "to another Study."
                ),
                403,
            )

        study = (
            ImagingStudy.objects
            .filter(
                study_instance_uid=
                    study_instance_uid
            )
            .first()
        )

        if study is None:
            raise ContractAPIException(
                "STUDY_NOT_FOUND",
                "Study not found.",
                404,
            )

        if (
            claims.get("study_id")
            != str(study.id)
        ):
            raise ContractAPIException(
                "DICOM_SCOPE_FORBIDDEN",
                (
                    "Viewer token Study ID "
                    "binding mismatch."
                ),
                403,
            )

        if study.status != "AVAILABLE":
            raise ContractAPIException(
                "STUDY_NOT_AVAILABLE",
                "Study is not AVAILABLE.",
                409,
            )

        data = query.validated_data

        try:
            result = qido_series(
                study_instance_uid,
                series_instance_uid=
                    data.get(
                        "SeriesInstanceUID"
                    ),
                modality=
                    data.get("Modality"),
                offset=
                    data.get("offset"),
                limit=
                    data.get("limit"),
            )

        except OrthancUnavailable as exc:
            raise ContractAPIException(
                "ORTHANC_UNAVAILABLE",
                "Orthanc QIDO is unavailable.",
                503,
            ) from exc

        record_audit_event(
            source_service="imaging",
            action="VIEW_DICOM_QIDO",
            resource_type="ImagingStudy",
            resource_id=study.id,
            patient_id=study.patient_id,
            outcome="SUCCESS",

            # ViewerPrincipal은 User FK가 아니므로
            # request를 그대로 넘기지 않는다.
            request=None,
            request_id=getattr(
                request,
                "request_id",
                None,
            ),
            after_json={
                "viewer_subject":
                    request.user.subject,
                "study_instance_uid":
                    study_instance_uid,
            },
        )

        response = Response(
            result,
            status=200,
        )

        response[
            "Content-Type"
        ] = "application/dicom+json"

        return response


class DicomArtifactStowView(APIView):
    authentication_classes = (
        ImagingServiceJWTAuthentication,
    )

    permission_classes = (
        RequiredImagingServiceScopePermission,
    )

    required_service_scope = "dicom.stow"

    @extend_schema(
        operation_id="api_dicom_003",
        summary="AI DICOM SEG/SR STOW 작업 등록",
        request=DicomStowSerializer,
        responses={
            202:
                DicomStowResponseSerializer,
        },
        tags=["dicom"],
    )
    def post(self, request):
        serializer = DicomStowSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        try:
            job, artifact, dicom = (
                register_dicom_stow(
                    data=
                        serializer.validated_data,
                    service_name=
                        request.user.service_name,
                    trace=getattr(
                        request,
                        "request_id",
                        uuid.uuid4(),
                    ),
                )
            )

        except ValueError as exc:
            code = str(exc)

            status_code = {
                "DICOM_CONTRACT_INVALID": 400,
                "SOP_INSTANCE_DUPLICATE": 409,
                "SPATIAL_METADATA_INVALID": 422,
            }.get(
                code,
                400,
            )

            raise ContractAPIException(
                code,
                code.replace(
                    "_",
                    " ",
                ).title(),
                status_code,
            ) from exc

        return Response(
            DicomStowResponseSerializer({
                "transfer_job_id":
                    job.id,
                "artifact_id":
                    artifact.id,
                "dicom_object_reference_id":
                    dicom.id,
                "status":
                    job.status,
            }).data,
            status=202,
        )
