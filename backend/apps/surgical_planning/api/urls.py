"""URL routes for surgical planning."""

from django.urls import path

from apps.surgical_planning.api.views import (
    SurgicalPlanClipDetailView, SurgicalPlanClipListCreateView,
    SurgicalPlanConfirmView, SurgicalPlanDetailView, SurgicalPlanDraftView,
    SurgicalPlanListCreateView, SurgicalPlanMessageListCreateView,
)

urlpatterns = [
    path("api/v1/surgical-plans", SurgicalPlanListCreateView.as_view(), name="surgical-plan-list-create"),
    path("api/v1/surgical-plans/<uuid:planning_id>", SurgicalPlanDetailView.as_view(), name="surgical-plan-detail"),
    path("api/v1/surgical-plans/<uuid:planning_id>/draft", SurgicalPlanDraftView.as_view(), name="surgical-plan-draft"),
    path("api/v1/surgical-plans/<uuid:planning_id>/confirm", SurgicalPlanConfirmView.as_view(), name="surgical-plan-confirm"),
    path("api/v1/surgical-plans/<uuid:planning_id>/clips", SurgicalPlanClipListCreateView.as_view(), name="surgical-plan-clips"),
    path("api/v1/surgical-plans/<uuid:planning_id>/clips/<uuid:clip_pk>", SurgicalPlanClipDetailView.as_view(), name="surgical-plan-clip-detail"),
    path("api/v1/surgical-plans/<uuid:planning_id>/messages", SurgicalPlanMessageListCreateView.as_view(), name="surgical-plan-messages"),
]
