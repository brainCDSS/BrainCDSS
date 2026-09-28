"""REST endpoints for surgical planning extension."""

from django.core.exceptions import (
    ValidationError as DjangoValidationError,
)
from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.errors import ContractAPIException
from apps.surgical_planning.api.permissions import (
    SurgicalPlanningPermission,
)
from apps.surgical_planning.api.serializers import (
    SurgicalPlanClipListSerializer,
    SurgicalPlanClipSerializer,
    SurgicalPlanClipUpdateSerializer,
    SurgicalPlanListSerializer,
    SurgicalPlanMessageListSerializer,
    SurgicalPlanMessageSerializer,
    SurgicalPlanSerializer,
    SurgicalPlanUpdateSerializer,
    SurgicalPlanVersionSerializer,
    SurgicalPlanWriteSerializer,
)
from apps.surgical_planning.models import (
    SurgicalPlan,
    SurgicalPlanStatus,
)
from apps.surgical_planning.selectors.planning import (
    get_surgical_plan,
    list_surgical_plans,
)
from apps.surgical_planning.services.planning import (
    SurgicalPlanningError,
    create_surgical_plan,
    create_surgical_plan_clip,
    create_surgical_plan_message,
    delete_surgical_plan_clip,
    update_surgical_plan,
    update_surgical_plan_clip,
)
from apps.patients.selectors.patients import can_view_patient


class PlanningAPIView(APIView):
    permission_classes = (
        SurgicalPlanningPermission,
    )

    def get_plan(self, request, planning_id):
        try:
            return get_surgical_plan(
                user=request.user,
                planning_id=planning_id
            )
        except SurgicalPlan.DoesNotExist as exc:
            raise Http404 from exc

    def service_call(
        self,
        function,
        **kwargs,
    ):
        try:
            return function(**kwargs)

        except SurgicalPlanningError as exc:
            raise ContractAPIException(
                exc.code,
                exc.detail,
                exc.status_code,
            ) from exc

        except DjangoValidationError as exc:
            raise ContractAPIException(
                "SURGICAL_PLANNING_VALIDATION_ERROR",
                "; ".join(exc.messages),
                400,
            ) from exc


class SurgicalPlanListCreateView(
    PlanningAPIView
):
    @extend_schema(
        operation_id="surgical_plans_list",
        responses=SurgicalPlanListSerializer,
    )
    def get(self, request):
        queryset = list_surgical_plans(
            user=request.user,
            patient_id=request.query_params.get(
                "patient_id"
            ),
            study_id=request.query_params.get(
                "study_id"
            ),
            status=request.query_params.get(
                "status"
            ),
        )

        serializer = SurgicalPlanSerializer(
            queryset,
            many=True,
        )

        return Response(
            {
                "count": queryset.count(),
                "results": serializer.data,
            }
        )

    @extend_schema(
        request=SurgicalPlanWriteSerializer,
        responses={
            201: SurgicalPlanSerializer
        },
    )
    def post(self, request):
        serializer = SurgicalPlanWriteSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        if not can_view_patient(
            request.user,
            serializer.validated_data["patient_id"],
        ):
            raise Http404

        plan = self.service_call(
            create_surgical_plan,
            user=request.user,
            request=request,
            **serializer.validated_data,
        )

        return Response(
            SurgicalPlanSerializer(plan).data,
            status=status.HTTP_201_CREATED,
        )


class SurgicalPlanDetailView(
    PlanningAPIView
):
    @extend_schema(
        operation_id="surgical_plans_retrieve",
        responses=SurgicalPlanSerializer,
    )
    def get(
        self,
        request,
        planning_id,
    ):
        return Response(
            SurgicalPlanSerializer(
                self.get_plan(request, planning_id)
            ).data
        )

    @extend_schema(
        request=SurgicalPlanUpdateSerializer,
        responses=SurgicalPlanSerializer,
    )
    def patch(
        self,
        request,
        planning_id,
    ):
        self.get_plan(request, planning_id)
        serializer = SurgicalPlanUpdateSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        data = dict(
            serializer.validated_data
        )

        expected_version = data.pop(
            "version"
        )
        requested_status = data.pop(
            "status",
            None,
        )

        audit_action = (
            "SURGICAL_PLAN_CANCELLED"
            if requested_status
            == SurgicalPlanStatus.CANCELLED
            else "SURGICAL_PLAN_UPDATED"
        )

        plan = self.service_call(
            update_surgical_plan,
            planning_id=planning_id,
            expected_version=expected_version,
            values=data,
            status=requested_status,
            user=request.user,
            request=request,
            audit_action=audit_action,
        )

        return Response(
            SurgicalPlanSerializer(plan).data
        )


class SurgicalPlanDraftView(
    PlanningAPIView
):
    @extend_schema(
        request=SurgicalPlanUpdateSerializer,
        responses=SurgicalPlanSerializer,
    )
    def post(
        self,
        request,
        planning_id,
    ):
        self.get_plan(request, planning_id)
        serializer = SurgicalPlanUpdateSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        data = dict(
            serializer.validated_data
        )

        expected_version = data.pop(
            "version"
        )

        data.pop(
            "status",
            None,
        )

        plan = self.service_call(
            update_surgical_plan,
            planning_id=planning_id,
            expected_version=expected_version,
            values=data,
            status=SurgicalPlanStatus.DRAFT,
            user=request.user,
            request=request,
            audit_action="SURGICAL_PLAN_DRAFT_SAVED",
        )

        return Response(
            SurgicalPlanSerializer(plan).data
        )


class SurgicalPlanConfirmView(
    PlanningAPIView
):
    @extend_schema(
        request=SurgicalPlanVersionSerializer,
        responses=SurgicalPlanSerializer,
    )
    def post(
        self,
        request,
        planning_id,
    ):
        self.get_plan(request, planning_id)
        serializer = SurgicalPlanVersionSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        plan = self.service_call(
            update_surgical_plan,
            planning_id=planning_id,
            expected_version=(
                serializer.validated_data[
                    "version"
                ]
            ),
            values={},
            status=SurgicalPlanStatus.CONFIRMED,
            user=request.user,
            request=request,
            audit_action="SURGICAL_PLAN_CONFIRMED",
        )

        return Response(
            SurgicalPlanSerializer(plan).data
        )


class SurgicalPlanClipListCreateView(
    PlanningAPIView
):
    @extend_schema(
        responses=SurgicalPlanClipListSerializer
    )
    def get(
        self,
        request,
        planning_id,
    ):
        plan = self.get_plan(request, planning_id)

        clips = plan.clips.all()

        return Response(
            {
                "count": clips.count(),
                "results": (
                    SurgicalPlanClipSerializer(
                        clips,
                        many=True,
                    ).data
                ),
            }
        )

    @extend_schema(
        request=SurgicalPlanClipSerializer,
        responses={
            201: SurgicalPlanClipSerializer
        },
    )
    def post(
        self,
        request,
        planning_id,
    ):
        self.get_plan(request, planning_id)
        serializer = SurgicalPlanClipSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        clip = self.service_call(
            create_surgical_plan_clip,
            planning_id=planning_id,
            values=dict(
                serializer.validated_data
            ),
            request=request,
        )

        return Response(
            SurgicalPlanClipSerializer(
                clip
            ).data,
            status=status.HTTP_201_CREATED,
        )


class SurgicalPlanClipDetailView(
    PlanningAPIView
):
    @extend_schema(
        request=SurgicalPlanClipUpdateSerializer,
        responses=SurgicalPlanClipSerializer,
    )
    def patch(
        self,
        request,
        planning_id,
        clip_pk,
    ):
        self.get_plan(request, planning_id)
        serializer = (
            SurgicalPlanClipUpdateSerializer(
                data=request.data,
                partial=True,
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        clip = self.service_call(
            update_surgical_plan_clip,
            planning_id=planning_id,
            clip_id=clip_pk,
            values=dict(
                serializer.validated_data
            ),
            request=request,
        )

        return Response(
            SurgicalPlanClipSerializer(
                clip
            ).data
        )

    @extend_schema(
        responses={204: None}
    )
    def delete(
        self,
        request,
        planning_id,
        clip_pk,
    ):
        self.get_plan(request, planning_id)
        self.service_call(
            delete_surgical_plan_clip,
            planning_id=planning_id,
            clip_id=clip_pk,
            request=request,
        )

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )


class SurgicalPlanMessageListCreateView(
    PlanningAPIView
):
    @extend_schema(
        responses=SurgicalPlanMessageListSerializer
    )
    def get(
        self,
        request,
        planning_id,
    ):
        plan = self.get_plan(request, planning_id)

        messages = (
            plan.messages
            .select_related(
                "sender",
                "sender__role",
            )
            .all()
        )

        return Response(
            {
                "count": messages.count(),
                "results": (
                    SurgicalPlanMessageSerializer(
                        messages,
                        many=True,
                    ).data
                ),
            }
        )

    @extend_schema(
        request=SurgicalPlanMessageSerializer,
        responses={
            201: SurgicalPlanMessageSerializer
        },
    )
    def post(
        self,
        request,
        planning_id,
    ):
        self.get_plan(request, planning_id)
        serializer = SurgicalPlanMessageSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        message = self.service_call(
            create_surgical_plan_message,
            planning_id=planning_id,
            sender=request.user,
            values=dict(
                serializer.validated_data
            ),
            request=request,
        )

        return Response(
            SurgicalPlanMessageSerializer(
                message
            ).data,
            status=status.HTTP_201_CREATED,
        )
