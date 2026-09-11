from django.core.paginator import (
    EmptyPage,
    Paginator,
)
from django.utils import timezone

from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.errors import (
    ContractAPIException,
)
from apps.audit.services.audit_event import (
    record_audit_event,
)
from apps.clinical_records.models import Encounter
from apps.imaging.api.imaging_order_serializers import (
    ImagingOrderCancelResponseSerializer,
    ImagingOrderCancelSerializer,
    ImagingOrderCreateSerializer,
    ImagingOrderListResponseSerializer,
    ImagingOrderQuerySerializer,
    ImagingOrderSerializer,
    ImagingOrderUpdateSerializer,
)
from apps.imaging.api.imaging_study_permissions import (
    ImagingOrderReadPermission,
    ImagingOrderWritePermission,
)
from apps.imaging.selectors.imaging_orders import (
    get_order_history,
    get_order_study,
    get_scoped_imaging_order,
    scoped_imaging_orders,
    user_can_access_encounter,
)
from apps.imaging.services.imaging_orders import (
    cancel_imaging_order,
    create_imaging_order,
    update_imaging_order,
)


def _page_url(request, page_number):
    if page_number is None:
        return None

    query = request.GET.copy()
    query["page"] = page_number

    return request.build_absolute_uri(
        f"{request.path}?{query.urlencode()}"
    )


def _user_payload(user):
    return {
        "user_id": user.id,
        "name": user.name,
        "role": user.role.code,
    }


def _study_payload(study):
    if study is None:
        return None

    return {
        "study_id": study.id,
        "study_instance_uid":
            study.study_instance_uid,
        "status": study.status,
    }


def _order_payload(
    order,
    *,
    detail=False,
):
    payload = {
        "order_id": order.id,
        "encounter_id": order.encounter_id,
        "patient_id": order.patient_id,
        "patient": {
            "patient_id": order.patient_id,
            "patient_no":
                order.patient.patient_no,
            "name":
                order.patient.name,
        },
        "accession_number":
            order.accession_number,
        "procedure_code":
            order.procedure_code,
        "procedure_name":
            order.procedure_name,
        "modality":
            order.modality,
        "priority":
            order.priority,
        "status":
            order.status,
        "reason":
            order.reason,
        "requested_by":
            _user_payload(
                order.requested_by
            ),
        "requested_at":
            order.requested_at,
        "scheduled_at":
            order.scheduled_at,
    }

    if detail:
        payload["study"] = _study_payload(
            get_order_study(order)
        )

        payload["status_history"] = [
            {
                "previous_status":
                    row.previous_status,
                "status":
                    row.status,
                "occurred_at":
                    row.occurred_at,
                "reason":
                    row.reason,
            }
            for row in get_order_history(order)
        ]

    return payload


class ImagingOrderListCreateView(APIView):

    def get_permissions(self):
        permission = (
            ImagingOrderWritePermission
            if self.request.method == "POST"
            else ImagingOrderReadPermission
        )

        return [permission()]

    @extend_schema(
        operation_id="api_img_001",
        summary="영상검사 오더 목록 조회",
        parameters=[
            ImagingOrderQuerySerializer,
        ],
        responses={
            200:
                ImagingOrderListResponseSerializer,
        },
        tags=["imaging"],
    )
    def get(self, request):
        serializer = ImagingOrderQuerySerializer(
            data=request.query_params
        )
        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data
        queryset = scoped_imaging_orders(
            request.user
        )

        if data.get("encounter_id"):
            queryset = queryset.filter(
                encounter_id=
                    data["encounter_id"]
            )

        if data.get("patient_id"):
            queryset = queryset.filter(
                patient_id=
                    data["patient_id"]
            )

        if data.get("status"):
            queryset = queryset.filter(
                status=data["status"]
            )

        if data.get("modality"):
            queryset = queryset.filter(
                modality=data["modality"]
            )

        if data.get("priority"):
            queryset = queryset.filter(
                priority=data["priority"]
            )

        if data.get("date_from"):
            queryset = queryset.filter(
                requested_at__date__gte=
                    data["date_from"]
            )

        if data.get("date_to"):
            queryset = queryset.filter(
                requested_at__date__lte=
                    data["date_to"]
            )

        queryset = queryset.order_by(
            "-requested_at",
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

        payload = {
            "count": paginator.count,
            "next": _page_url(
                request,
                (
                    page.next_page_number()
                    if page.has_next()
                    else None
                ),
            ),
            "previous": _page_url(
                request,
                (
                    page.previous_page_number()
                    if page.has_previous()
                    else None
                ),
            ),
            "results": [
                _order_payload(order)
                for order in page.object_list
            ],
        }

        record_audit_event(
            source_service="imaging",
            action="VIEW_IMAGING_ORDERS",
            resource_type="ImagingOrder",
            resource_id=None,
            outcome="SUCCESS",
            request=request,
        )

        return Response(
            ImagingOrderListResponseSerializer(
                payload
            ).data
        )

    @extend_schema(
        operation_id="api_img_012",
        summary="영상검사 Order 생성",
        request=ImagingOrderCreateSerializer,
        responses={
            201: ImagingOrderSerializer,
        },
        tags=["imaging"],
    )
    def post(self, request):
        serializer = ImagingOrderCreateSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data

        encounter = (
            Encounter.objects
            .select_related(
                "patient",
                "appointment",
                "appointment__clinician",
                "appointment__clinician__user",
            )
            .filter(
                pk=data["encounter_id"]
            )
            .first()
        )

        if encounter is None:
            raise ContractAPIException(
                "ENCOUNTER_NOT_FOUND",
                "Encounter not found.",
                404,
            )

        if (
            str(encounter.patient_id)
            != str(data["patient_id"])
        ):
            raise ContractAPIException(
                "ORDER_INPUT_INVALID",
                (
                    "patient_id does not match "
                    "encounter.patient_id."
                ),
                400,
            )

        if encounter.status not in {
            "REGISTERED",
            "IN_PROGRESS",
        }:
            raise ContractAPIException(
                "ENCOUNTER_INACTIVE",
                "Encounter is not active.",
                409,
            )

        if not user_can_access_encounter(
            user=request.user,
            encounter=encounter,
        ):
            raise ContractAPIException(
                "ENCOUNTER_FORBIDDEN",
                "Encounter access forbidden.",
                403,
            )

        order = create_imaging_order(
            encounter=encounter,
            user=request.user,
            data=data,
            request=request,
        )

        return Response(
            ImagingOrderSerializer(
                _order_payload(order)
            ).data,
            status=201,
        )


class ImagingOrderDetailUpdateView(APIView):

    def get_permissions(self):
        permission = (
            ImagingOrderWritePermission
            if self.request.method == "PATCH"
            else ImagingOrderReadPermission
        )

        return [permission()]

    @extend_schema(
        operation_id="api_img_002",
        summary="영상검사 오더 상세 조회",
        responses={
            200: ImagingOrderSerializer,
        },
        tags=["imaging"],
    )
    def get(
        self,
        request,
        order_id,
    ):
        order = get_scoped_imaging_order(
            user=request.user,
            order_id=order_id,
        )

        if order is None:
            raise ContractAPIException(
                "IMAGING_ORDER_NOT_FOUND",
                "Imaging order not found.",
                404,
            )

        record_audit_event(
            source_service="imaging",
            action="VIEW_IMAGING_ORDER",
            resource_type="ImagingOrder",
            resource_id=order.id,
            patient_id=order.patient_id,
            outcome="SUCCESS",
            request=request,
        )

        return Response(
            ImagingOrderSerializer(
                _order_payload(
                    order,
                    detail=True,
                )
            ).data
        )

    @extend_schema(
        operation_id="api_img_013",
        summary="영상검사 Order 변경",
        request=ImagingOrderUpdateSerializer,
        responses={
            200: ImagingOrderSerializer,
        },
        tags=["imaging"],
    )
    def patch(
        self,
        request,
        order_id,
    ):
        serializer = ImagingOrderUpdateSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        order = get_scoped_imaging_order(
            user=request.user,
            order_id=order_id,
        )

        if order is None:
            raise ContractAPIException(
                "ORDER_NOT_FOUND",
                "Imaging order not found.",
                404,
            )

        if (
            order.requested_by_id
            != request.user.id
            and not user_can_access_encounter(
                user=request.user,
                encounter=order.encounter,
            )
        ):
            raise ContractAPIException(
                "ORDER_CHANGE_NOT_ALLOWED",
                "Order change is not allowed.",
                409,
            )

        if order.status not in {
            "PLACED",
            "SCHEDULED",
            "HELD",
        }:
            raise ContractAPIException(
                "ORDER_CHANGE_NOT_ALLOWED",
                (
                    "Order cannot be changed "
                    "after imaging has started."
                ),
                409,
            )

        scheduled_at = (
            serializer.validated_data.get(
                "scheduled_at"
            )
        )

        if (
            scheduled_at is not None
            and scheduled_at <= timezone.now()
        ):
            raise ContractAPIException(
                "INVALID_SCHEDULE",
                "scheduled_at must be in the future.",
                422,
            )

        order = update_imaging_order(
            order_id=order.id,
            user=request.user,
            data=serializer.validated_data,
            request=request,
        )

        order = get_scoped_imaging_order(
            user=request.user,
            order_id=order.id,
        )

        return Response(
            ImagingOrderSerializer(
                _order_payload(
                    order,
                    detail=True,
                )
            ).data
        )


class ImagingOrderCancelView(APIView):
    permission_classes = (
        ImagingOrderWritePermission,
    )

    @extend_schema(
        operation_id="api_img_014",
        summary="영상검사 Order 취소",
        request=ImagingOrderCancelSerializer,
        responses={
            200:
                ImagingOrderCancelResponseSerializer,
        },
        tags=["imaging"],
    )
    def post(
        self,
        request,
        order_id,
    ):
        serializer = ImagingOrderCancelSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        order = get_scoped_imaging_order(
            user=request.user,
            order_id=order_id,
        )

        if order is None:
            raise ContractAPIException(
                "ORDER_NOT_FOUND",
                "Imaging order not found.",
                404,
            )

        if (
            order.requested_by_id
            != request.user.id
            and not user_can_access_encounter(
                user=request.user,
                encounter=order.encounter,
            )
        ):
            raise ContractAPIException(
                "ORDER_CANCEL_NOT_ALLOWED",
                "Order cancel is not allowed.",
                409,
            )

        if order.status not in {
            "PLACED",
            "SCHEDULED",
            "HELD",
        }:
            raise ContractAPIException(
                "ORDER_CANCEL_NOT_ALLOWED",
                (
                    "Order cannot be cancelled "
                    "after imaging has started."
                ),
                409,
            )

        order, history = cancel_imaging_order(
            order_id=order.id,
            user=request.user,
            reason=serializer.validated_data[
                "reason"
            ],
            request=request,
        )

        payload = {
            "order_id": order.id,
            "status": order.status,
            "reason": history.reason,
            "cancelled_at":
                history.occurred_at,
        }

        return Response(
            ImagingOrderCancelResponseSerializer(
                payload
            ).data
        )
