from django.core.paginator import (
    EmptyPage,
    Paginator,
)
from django.db.models import Exists, OuterRef
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.errors import ContractAPIException
from apps.audit.services.audit_event import (
    record_audit_event,
)
from apps.imaging.api.imaging_study_permissions import (
    ImagingSeriesPermission,
    ImagingStudyPermission,
)
from apps.imaging.api.imaging_study_serializers import (
    ImagingSeriesQuerySerializer,
    ImagingSeriesResponseSerializer,
    ImagingStudyDetailSerializer,
    ImagingStudyListQuerySerializer,
    ImagingStudyListResponseSerializer,
    StudyAIHistoryQuerySerializer,
    StudyAIHistoryResponseSerializer,
    ImagingSeriesDetailSerializer,
    KeyImageCreateSerializer,
    KeyImageListSerializer,
    KeyImageSerializer,
)
from apps.imaging.models import ImagingStudy, NiftiArtifact
from apps.imaging.selectors.imaging_studies import (
    filter_imaging_studies,
    get_scoped_imaging_study,
    get_study_series,
    scoped_imaging_studies,
    list_study_ai_analyses,
    get_scoped_series,
    list_derived_dicom_objects,
    list_key_images,
)


def _patient_summary(study):
    if study.patient_id is None:
        return None

    return {
        "patient_id": study.patient_id,
        "patient_no": study.patient.patient_no,
        "name": study.patient.name,
        "birth_date": study.patient.birth_date,
        "estimated_age": study.patient.estimated_age,
        "sex": study.patient.sex,
    }


def _latest_analysis(study):
    if study.latest_analysis_id is None:
        return None

    return {
        "analysis_id": study.latest_analysis_id,
        "status": study.latest_analysis_status,
    }


def _current_report(study):
    if study.current_report_id is None:
        return None

    return {
        "report_id": study.current_report_id,
        "status": study.current_report_status,
    }


def _scan_type(study):
    if getattr(study, "has_mra_input", False):
        return "MRA"

    order = study.imaging_order

    if order is None:
        return None

    text = (
        f"{order.procedure_code} "
        f"{order.procedure_name}"
    ).upper()

    if (
        "MRA" in text
        or "MR ANGIO" in text
        or "MR ANGIOGRAPH" in text
    ):
        return "MRA"

    if (
        "CTA" in text
        or "CT ANGIO" in text
        or "CT ANGIOGRAPH" in text
    ):
        return "CTA"

    return None


def _study_list_item(study):
    modalities = (
        study.modalities
        if isinstance(study.modalities, list)
        else []
    )

    return {
        "study_id": study.id,
        "accession_number": study.accession_number,
        "study_datetime": study.study_datetime,
        "modalities": modalities,
        "status": study.status,
        "series_count": study.series_count,
        "instance_count": study.instance_count,
        "latest_analysis": _latest_analysis(study),
        "current_report": _current_report(study),
        "critical_finding": bool(
            study.current_report_critical
        ),
        "patient": _patient_summary(study),
        "scan_type": _scan_type(study),
    }


def _series_item(series):
    return {
        "series_id": series.id,
        "series_instance_uid":
            series.series_instance_uid,
        "series_number": series.series_number,
        "modality": series.modality,
        "series_description":
            series.series_description,
        "instance_count": series.instance_count,
        "slice_thickness": (
            float(series.slice_thickness)
            if series.slice_thickness is not None
            else None
        ),
        "is_complete": series.is_complete,
        "is_ai_eligible": series.is_ai_eligible,
        "ai_exclusion_reason":
            series.ai_exclusion_reason,
    }


def _page_url(request, number):
    if number is None:
        return None

    query = request.query_params.copy()
    query["page"] = str(number)

    return request.build_absolute_uri(
        f"{request.path}?{query.urlencode()}"
    )


class ImagingStudyListView(APIView):
    permission_classes = (
        ImagingStudyPermission,
    )

    @extend_schema(
        operation_id="api_img_003",
        summary="영상 Study Worklist 조회",
        parameters=[
            ImagingStudyListQuerySerializer
        ],
        responses={
            200: ImagingStudyListResponseSerializer
        },
        tags=["imaging"],
    )
    def get(self, request):
        query_serializer = (
            ImagingStudyListQuerySerializer(
                data=request.query_params
            )
        )
        query_serializer.is_valid(
            raise_exception=True
        )

        params = query_serializer.validated_data

        queryset = scoped_imaging_studies(
            request.user
        )
        queryset = filter_imaging_studies(
            queryset,
            params,
        )
        queryset = queryset.annotate(
            has_mra_input=Exists(
                NiftiArtifact.objects.filter(
                    series__study_id=OuterRef("pk"),
                    role="MRA",
                )
            )
        )

        paginator = Paginator(
            queryset,
            params["page_size"],
        )

        try:
            page = paginator.page(
                params["page"]
            )
        except EmptyPage as exc:
            raise ContractAPIException(
                "INVALID_QUERY_PARAMETER",
                "Requested page does not exist.",
                400,
            ) from exc

        payload = {
            "count": paginator.count,
            "next": _page_url(
                request,
                page.next_page_number()
                if page.has_next()
                else None,
            ),
            "previous": _page_url(
                request,
                page.previous_page_number()
                if page.has_previous()
                else None,
            ),
            "results": [
                _study_list_item(item)
                for item in page.object_list
            ],
        }

        response_serializer = (
            ImagingStudyListResponseSerializer(
                payload
            )
        )

        record_audit_event(
            source_service="imaging",
            action="VIEW_IMAGING_STUDY_LIST",
            resource_type="ImagingStudy",
            outcome="SUCCESS",
            request=request,
            patient_id=params.get(
                "patient_id"
            ),
        )

        return Response(
            response_serializer.data
        )


class ImagingStudyDetailView(APIView):
    permission_classes = (
        ImagingStudyPermission,
    )

    @extend_schema(
        operation_id="api_img_004",
        summary="영상 Study 상세 조회",
        responses={
            200: ImagingStudyDetailSerializer
        },
        tags=["imaging"],
    )
    def get(
        self,
        request,
        study_id,
    ):
        try:
            study = get_scoped_imaging_study(
                user=request.user,
                study_id=study_id,
            )
        except ImagingStudy.DoesNotExist as exc:
            raise ContractAPIException(
                "IMAGING_STUDY_NOT_FOUND",
                "Imaging study not found.",
                404,
            ) from exc

        series = get_study_series(study.id)

        payload = {
            "study_id": study.id,
            "study_instance_uid":
                study.study_instance_uid,
            "accession_number":
                study.accession_number,
            "study_datetime":
                study.study_datetime,
            "status": study.status,
            "patient": _patient_summary(study),
            "series": [
                _series_item(item)
                for item in series
            ],
            "latest_analysis":
                _latest_analysis(study),
            "current_report":
                _current_report(study),
        }

        serializer = ImagingStudyDetailSerializer(
            payload
        )

        record_audit_event(
            source_service="imaging",
            action="VIEW_IMAGING_STUDY",
            resource_type="ImagingStudy",
            resource_id=study.id,
            patient_id=study.patient_id,
            outcome="SUCCESS",
            request=request,
        )

        return Response(serializer.data)


class ImagingStudySeriesView(APIView):
    permission_classes = (
        ImagingSeriesPermission,
    )

    @extend_schema(
        operation_id="api_img_005",
        summary="Study Series 목록 조회",
        parameters=[
            ImagingSeriesQuerySerializer,
        ],
        responses={
            200: ImagingSeriesResponseSerializer,
        },
        tags=["imaging"],
    )
    def get(
        self,
        request,
        study_id,
    ):
        query_serializer = ImagingSeriesQuerySerializer(
            data=request.query_params
        )
        query_serializer.is_valid(
            raise_exception=True
        )

        try:
            study = get_scoped_imaging_study(
                user=request.user,
                study_id=study_id,
            )
        except ImagingStudy.DoesNotExist as exc:
            raise ContractAPIException(
                "IMAGING_STUDY_NOT_FOUND",
                "Imaging study not found.",
                404,
            ) from exc

        queryset = get_study_series(
            study.id
        )

        params = query_serializer.validated_data

        if "modality" in params:
            queryset = queryset.filter(
                modality=params["modality"]
            )

        if "ai_eligible" in params:
            queryset = queryset.filter(
                is_ai_eligible=params[
                    "ai_eligible"
                ]
            )

        if "complete" in params:
            queryset = queryset.filter(
                is_complete=params[
                    "complete"
                ]
            )

        payload = {
            "study_id": study.id,
            "series": [
                _series_item(series)
                for series in queryset
            ],
        }

        serializer = ImagingSeriesResponseSerializer(
            payload
        )

        record_audit_event(
            source_service="imaging",
            action="VIEW_IMAGING_STUDY_SERIES",
            resource_type="ImagingStudy",
            resource_id=study.id,
            patient_id=study.patient_id,
            outcome="SUCCESS",
            request=request,
        )

        return Response(
            serializer.data
        )


class ImagingStudyAIHistoryView(APIView):
    permission_classes = (
        ImagingSeriesPermission,
    )

    @extend_schema(
        operation_id="api_img_009",
        summary="Study AI 분석 이력 조회",
        parameters=[
            StudyAIHistoryQuerySerializer,
        ],
        responses={
            200: StudyAIHistoryResponseSerializer,
        },
        tags=["imaging"],
    )
    def get(
        self,
        request,
        study_id,
    ):
        query_serializer = (
            StudyAIHistoryQuerySerializer(
                data=request.query_params
            )
        )
        query_serializer.is_valid(
            raise_exception=True
        )

        params = query_serializer.validated_data

        try:
            study = get_scoped_imaging_study(
                user=request.user,
                study_id=study_id,
            )
        except ImagingStudy.DoesNotExist as exc:
            raise ContractAPIException(
                "IMAGING_STUDY_NOT_FOUND",
                "Imaging study not found.",
                404,
            ) from exc

        queryset = list_study_ai_analyses(
            study_id=study.id,
            status=params.get("status"),
            analysis_type=params.get(
                "analysis_type"
            ),
        )

        paginator = Paginator(
            queryset,
            params["page_size"],
        )

        try:
            page_obj = paginator.page(
                params["page"]
            )
        except EmptyPage as exc:
            raise ContractAPIException(
                "INVALID_QUERY_PARAMETER",
                "Requested page does not exist.",
                400,
            ) from exc

        results = []

        for analysis in page_obj.object_list:
            model_version = (
                analysis.model_version
            )
            model = model_version.model

            result_summary = None

            if analysis.result_exists:
                result_summary = {
                    "is_positive":
                        analysis.result_is_positive,
                    "total_volume_ml": (
                        float(
                            analysis.result_total_volume_ml
                        )
                        if (
                            analysis.result_total_volume_ml
                            is not None
                        )
                        else None
                    ),
                }

            results.append(
                {
                    "analysis_id":
                        analysis.id,
                    "analysis_type":
                        analysis.analysis_type,
                    "status":
                        analysis.status,
                    "stage":
                        analysis.stage,
                    "model": {
                        "code":
                            model.code,
                        "version":
                            model_version.version,
                    },
                    "attempt_count":
                        analysis.attempt_count,
                    "requested_at":
                        analysis.requested_at,
                    "result_summary":
                        result_summary,
                }
            )

        payload = {
            "study_id": study.id,
            "count": paginator.count,
            "next": _page_url(
                request,
                (
                    page_obj.next_page_number()
                    if page_obj.has_next()
                    else None
                ),
            ),
            "previous": _page_url(
                request,
                (
                    page_obj.previous_page_number()
                    if page_obj.has_previous()
                    else None
                ),
            ),
            "results": results,
        }

        serializer = (
            StudyAIHistoryResponseSerializer(
                payload
            )
        )

        record_audit_event(
            source_service="imaging",
            action="VIEW_STUDY_AI_ANALYSES",
            resource_type="ImagingStudy",
            resource_id=study.id,
            patient_id=study.patient_id,
            outcome="SUCCESS",
            request=request,
        )

        return Response(
            serializer.data
        )



class ImagingSeriesDetailView(APIView):
    permission_classes = (
        ImagingSeriesPermission,
    )

    @extend_schema(
        operation_id="api_img_006",
        summary="영상 Series 상세 조회",
        responses={
            200: ImagingSeriesDetailSerializer,
        },
        tags=["imaging"],
    )
    def get(
        self,
        request,
        series_id,
    ):
        series = get_scoped_series(
            user=request.user,
            series_id=series_id,
        )

        if series is None:
            raise ContractAPIException(
                "IMAGING_SERIES_NOT_FOUND",
                "Imaging series not found.",
                404,
            )

        derived_objects = (
            list_derived_dicom_objects(
                series.id
            )
        )

        payload = {
            "series_id": series.id,
            "study_id": series.study_id,
            "series_instance_uid":
                series.series_instance_uid,
            "modality": series.modality,
            "protocol_name":
                series.protocol_name,
            "series_description":
                series.series_description,
            "instance_count":
                series.instance_count,
            "frame_count":
                series.frame_count,
            "rows": series.rows,
            "columns": series.columns,
            "slice_thickness": (
                float(series.slice_thickness)
                if series.slice_thickness
                is not None
                else None
            ),
            "is_complete":
                series.is_complete,
            "is_ai_eligible":
                series.is_ai_eligible,
            "ai_exclusion_reason":
                series.ai_exclusion_reason,
            "derived_objects": [
                {
                    "type":
                        item.object_type,
                    "sop_instance_uid":
                        item.sop_instance_uid,
                }
                for item
                in derived_objects
            ],
        }

        serializer = (
            ImagingSeriesDetailSerializer(
                payload
            )
        )

        record_audit_event(
            source_service="imaging",
            action="VIEW_IMAGING_SERIES",
            resource_type="SeriesReference",
            resource_id=series.id,
            patient_id=series.study.patient_id,
            outcome="SUCCESS",
            request=request,
        )

        return Response(
            serializer.data
        )


class ImagingStudyKeyImagesView(APIView):
    permission_classes = (
        ImagingSeriesPermission,
    )

    @extend_schema(
        operation_id="api_img_020",
        summary="대표 영상 목록 조회",
        responses={
            200: KeyImageListSerializer,
        },
        tags=["imaging"],
    )
    def get(
        self,
        request,
        study_id,
    ):
        try:
            study = get_scoped_imaging_study(
                user=request.user,
                study_id=study_id,
            )
        except ImagingStudy.DoesNotExist as exc:
            raise ContractAPIException(
                "IMAGING_STUDY_NOT_FOUND",
                "Imaging study not found.",
                404,
            ) from exc

        queryset = list_key_images(
            study.id
        )

        payload = {
            "results": [
                {
                    "key_image_id": item.id,
                    "study_id": item.study_id,
                    "sop_instance_uid":
                        item.sop_instance_uid,
                    "frame_number":
                        item.frame_number,
                    "label": item.label,
                    "selected_by": {
                        "user_id":
                            item.selected_by_id,
                        "name":
                            item.selected_by.name,
                        "role":
                            item.selected_by.role.code,
                    },
                    "selected_at":
                        item.selected_at,
                }
                for item in queryset
            ]
        }

        serializer = KeyImageListSerializer(
            payload
        )

        return Response(
            serializer.data
        )

    @extend_schema(
        operation_id="api_img_021",
        summary="대표 영상 선택",
        request=KeyImageCreateSerializer,
        responses={
            201: KeyImageSerializer,
        },
        tags=["imaging"],
    )
    def post(
        self,
        request,
        study_id,
    ):
        from django.db import transaction
        from django.utils import timezone

        from apps.imaging.models import (
            DicomObjectReference,
            KeyImageSelection,
        )

        serializer = KeyImageCreateSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        try:
            study = get_scoped_imaging_study(
                user=request.user,
                study_id=study_id,
            )
        except ImagingStudy.DoesNotExist as exc:
            raise ContractAPIException(
                "IMAGING_STUDY_NOT_FOUND",
                "Imaging study not found.",
                404,
            ) from exc

        data = serializer.validated_data

        dicom = (
            DicomObjectReference.objects
            .select_related("series")
            .filter(
                study_id=study.id,
                sop_instance_uid=
                    data["sop_instance_uid"],
                object_type="SOURCE_IMAGE",
            )
            .first()
        )

        if dicom is None:
            raise ContractAPIException(
                "STUDY_OR_INSTANCE_NOT_FOUND",
                (
                    "SOURCE_IMAGE SOP instance "
                    "was not found in this study."
                ),
                404,
            )

        frame_number = data.get(
            "frame_number"
        )

        if frame_number is not None:
            series = dicom.series

            if (
                series is None
                or series.frame_count <= 0
                or frame_number > series.frame_count
            ):
                raise ContractAPIException(
                    "FRAME_INVALID",
                    (
                        "frame_number is outside "
                        "the source series range."
                    ),
                    422,
                )

        with transaction.atomic():
            key_image = (
                KeyImageSelection.objects.create(
                    study=study,
                    sop_instance_uid=
                        dicom.sop_instance_uid,
                    frame_number=frame_number,
                    label=data["label"],
                    selected_by=request.user,
                    selected_at=timezone.now(),
                )
            )

            record_audit_event(
                source_service="imaging",
                action="SELECT_KEY_IMAGE",
                resource_type="KeyImageSelection",
                resource_id=key_image.id,
                patient_id=study.patient_id,
                outcome="SUCCESS",
                request=request,
                after_json={
                    "study_id":
                        str(study.id),
                    "sop_instance_uid":
                        dicom.sop_instance_uid,
                    "frame_number":
                        frame_number,
                },
            )

        payload = {
            "key_image_id": key_image.id,
            "study_id": study.id,
            "sop_instance_uid":
                key_image.sop_instance_uid,
            "frame_number":
                key_image.frame_number,
            "label":
                key_image.label,
            "selected_by": {
                "user_id":
                    request.user.id,
                "name":
                    request.user.name,
                "role":
                    request.user.role.code,
            },
            "selected_at":
                key_image.selected_at,
        }

        return Response(
            KeyImageSerializer(payload).data,
            status=201,
        )
