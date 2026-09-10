"""REST endpoints for surgical planning persistence."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.surgical_planning.api.permissions import SurgicalPlanningPermission
from apps.surgical_planning.api.serializers import (
    SurgicalPlanClipListSerializer, SurgicalPlanClipSerializer, SurgicalPlanClipUpdateSerializer,
    SurgicalPlanListSerializer, SurgicalPlanMessageListSerializer, SurgicalPlanMessageSerializer, SurgicalPlanSerializer,
    SurgicalPlanUpdateSerializer, SurgicalPlanVersionSerializer, SurgicalPlanWriteSerializer,
)
from apps.surgical_planning.models import SurgicalPlanClip, SurgicalPlanStatus
from apps.surgical_planning.selectors.planning import get_surgical_plan, list_surgical_plans
from apps.surgical_planning.services.planning import create_surgical_plan, update_surgical_plan


class PlanningAPIView(APIView):
    permission_classes = (SurgicalPlanningPermission,)

    def get_plan(self, planning_id):
        try:
            return get_surgical_plan(planning_id=planning_id)
        except self.plan_model.DoesNotExist as exc:
            raise Http404 from exc

    @property
    def plan_model(self):
        from apps.surgical_planning.models import SurgicalPlan
        return SurgicalPlan

    def service_call(self, function, **kwargs):
        try:
            return function(**kwargs)
        except ObjectDoesNotExist as exc:
            raise Http404 from exc
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages) from exc


class SurgicalPlanListCreateView(PlanningAPIView):
    @extend_schema(responses=SurgicalPlanListSerializer)
    def get(self, request):
        queryset = list_surgical_plans(patient_id=request.query_params.get("patient_id"), study_id=request.query_params.get("study_id"), status=request.query_params.get("status"))
        serializer = SurgicalPlanSerializer(queryset, many=True)
        return Response({"count": queryset.count(), "results": serializer.data})

    @extend_schema(request=SurgicalPlanWriteSerializer, responses={201: SurgicalPlanSerializer})
    def post(self, request):
        serializer = SurgicalPlanWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = self.service_call(create_surgical_plan, user=request.user, **serializer.validated_data)
        return Response(SurgicalPlanSerializer(plan).data, status=status.HTTP_201_CREATED)


class SurgicalPlanDetailView(PlanningAPIView):
    @extend_schema(responses=SurgicalPlanSerializer)
    def get(self, request, planning_id):
        return Response(SurgicalPlanSerializer(self.get_plan(planning_id)).data)

    @extend_schema(request=SurgicalPlanUpdateSerializer, responses=SurgicalPlanSerializer)
    def patch(self, request, planning_id):
        serializer = SurgicalPlanUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        expected_version = data.pop("version")
        requested_status = data.pop("status", None)
        plan = self.service_call(update_surgical_plan, planning_id=planning_id, expected_version=expected_version, values=data, status=requested_status, user=request.user)
        return Response(SurgicalPlanSerializer(plan).data)


class SurgicalPlanDraftView(PlanningAPIView):
    @extend_schema(request=SurgicalPlanUpdateSerializer, responses=SurgicalPlanSerializer)
    def post(self, request, planning_id):
        serializer = SurgicalPlanUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        expected_version = data.pop("version")
        data.pop("status", None)
        plan = self.service_call(update_surgical_plan, planning_id=planning_id, expected_version=expected_version, values=data, status=SurgicalPlanStatus.DRAFT, user=request.user)
        return Response(SurgicalPlanSerializer(plan).data)


class SurgicalPlanConfirmView(PlanningAPIView):
    @extend_schema(request=SurgicalPlanVersionSerializer, responses=SurgicalPlanSerializer)
    def post(self, request, planning_id):
        serializer = SurgicalPlanVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = self.service_call(update_surgical_plan, planning_id=planning_id, expected_version=serializer.validated_data["version"], values={}, status=SurgicalPlanStatus.CONFIRMED, user=request.user)
        return Response(SurgicalPlanSerializer(plan).data)


class SurgicalPlanClipListCreateView(PlanningAPIView):
    @extend_schema(responses=SurgicalPlanClipListSerializer)
    def get(self, request, planning_id):
        plan = self.get_plan(planning_id)
        return Response({"count": plan.clips.count(), "results": SurgicalPlanClipSerializer(plan.clips.all(), many=True).data})

    @extend_schema(request=SurgicalPlanClipSerializer, responses={201: SurgicalPlanClipSerializer})
    def post(self, request, planning_id):
        plan = self.get_plan(planning_id)
        serializer = SurgicalPlanClipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        clip = serializer.save(planning=plan)
        return Response(SurgicalPlanClipSerializer(clip).data, status=status.HTTP_201_CREATED)


class SurgicalPlanClipDetailView(PlanningAPIView):
    def get_clip(self, planning_id, clip_pk):
        try:
            return SurgicalPlanClip.objects.get(pk=clip_pk, planning_id=planning_id)
        except SurgicalPlanClip.DoesNotExist as exc:
            raise Http404 from exc

    @extend_schema(request=SurgicalPlanClipUpdateSerializer, responses=SurgicalPlanClipSerializer)
    def patch(self, request, planning_id, clip_pk):
        clip = self.get_clip(planning_id, clip_pk)
        serializer = SurgicalPlanClipUpdateSerializer(clip, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(SurgicalPlanClipSerializer(clip).data)

    @extend_schema(responses={204: None})
    def delete(self, request, planning_id, clip_pk):
        self.get_clip(planning_id, clip_pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SurgicalPlanMessageListCreateView(PlanningAPIView):
    @extend_schema(responses=SurgicalPlanMessageListSerializer)
    def get(self, request, planning_id):
        plan = self.get_plan(planning_id)
        messages = plan.messages.select_related("sender", "sender__role").all()
        return Response({"count": messages.count(), "results": SurgicalPlanMessageSerializer(messages, many=True).data})

    @extend_schema(request=SurgicalPlanMessageSerializer, responses={201: SurgicalPlanMessageSerializer})
    def post(self, request, planning_id):
        plan = self.get_plan(planning_id)
        serializer = SurgicalPlanMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save(planning=plan, sender=request.user)
        return Response(SurgicalPlanMessageSerializer(message).data, status=status.HTTP_201_CREATED)
