from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.ai_analysis.models import AIAnalysis
from apps.patients.models import PatientCareAssignment


class Command(BaseCommand):
    help = "Assign all patients with AI analyses to a clinician."

    def add_arguments(self, parser):
        parser.add_argument("--login-id", required=True)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        clinician = User.objects.filter(login_id=options["login_id"], is_active=True).first()
        if clinician is None:
            raise CommandError("CLINICIAN_NOT_FOUND")

        patient_ids = list(
            AIAnalysis.objects.filter(study__patient_id__isnull=False)
            .values_list("study__patient_id", flat=True)
            .distinct()
        )
        if not patient_ids:
            raise CommandError("NO_AI_ANALYSIS_PATIENTS")

        existing = set(
            PatientCareAssignment.objects.filter(
                clinician=clinician,
                patient_id__in=patient_ids,
                role=PatientCareAssignment.AssignmentRole.PRIMARY,
                status=PatientCareAssignment.Status.ACTIVE,
            ).values_list("patient_id", flat=True)
        )
        pending = [patient_id for patient_id in patient_ids if patient_id not in existing]
        if not options["dry_run"]:
            with transaction.atomic():
                PatientCareAssignment.objects.bulk_create([
                    PatientCareAssignment(
                        patient_id=patient_id,
                        clinician=clinician,
                        role=PatientCareAssignment.AssignmentRole.PRIMARY,
                        source=PatientCareAssignment.Source.AI_ANALYSIS,
                    )
                    for patient_id in pending
                ])
        self.stdout.write(
            self.style.SUCCESS(
                f"AI_PATIENT_ASSIGNMENT clinician={clinician.login_id} total={len(patient_ids)} created={len(pending)} existing={len(existing)}"
            )
        )
