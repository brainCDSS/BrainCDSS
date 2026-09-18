from django.test import TestCase

from apps.accounts.models import Role, User
from apps.patients.models import Patient, PatientCareAssignment
from apps.patients.selectors.patients import can_view_patient, list_patients


class PatientCareAssignmentSelectorTests(TestCase):
    def setUp(self):
        role = Role.objects.create(code="NEUROLOGIST", name="Neurologist")
        self.clinician = User.objects.create_user("neuro-test", "password", name="Neurologist", role=role)
        self.other_clinician = User.objects.create_user("neuro-other", "password", name="Other", role=role)
        self.assigned = Patient.objects.create(patient_no="P-ASSIGNED", name="Assigned", created_by=self.clinician)
        self.other = Patient.objects.create(patient_no="P-OTHER", name="Other", created_by=self.clinician)

    def test_active_assignment_scopes_patient_list_and_detail_access(self):
        PatientCareAssignment.objects.create(
            patient=self.assigned,
            clinician=self.clinician,
            role=PatientCareAssignment.AssignmentRole.PRIMARY,
            source=PatientCareAssignment.Source.AI_ANALYSIS,
        )

        self.assertEqual(list(list_patients(actor=self.clinician)), [self.assigned])
        self.assertTrue(can_view_patient(self.clinician, self.assigned.id))
        self.assertFalse(can_view_patient(self.clinician, self.other.id))

    def test_clinician_without_assignments_cannot_access_patients(self):
        self.assertEqual(list(list_patients(actor=self.other_clinician)), [])
        self.assertFalse(can_view_patient(self.other_clinician, self.assigned.id))
