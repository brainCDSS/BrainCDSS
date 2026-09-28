"""Medication master administration."""

from django.contrib import admin

from apps.medications.models import MedicationDiseaseGroup


@admin.register(MedicationDiseaseGroup)
class MedicationDiseaseGroupAdmin(admin.ModelAdmin):
    list_display = ("medication", "disease_group", "is_active", "updated_at")
    list_filter = ("disease_group", "is_active")
    search_fields = ("medication__medication_name", "medication__medication_code")
