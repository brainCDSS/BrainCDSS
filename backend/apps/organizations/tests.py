from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import Role, RoleCode, User
from apps.organizations.models import Clinician, Department, Hospital


class OrganizationStaffReferenceAPITests(APITestCase):
    def setUp(self):
        nurse_role = Role.objects.get(code=RoleCode.NURSE)
        neurologist_role = Role.objects.create(
            code=RoleCode.NEUROLOGIST,
            name="신경과",
        )
        self.nurse = User.objects.create_user(
            login_id="organization-nurse",
            password="test-password",
            name="테스트 간호사",
            role=nurse_role,
        )
        self.neurologist = User.objects.create_user(
            login_id="organization-neurologist",
            password="test-password",
            name="테스트 신경과",
            role=neurologist_role,
        )
        neurosurgeon_role = Role.objects.create(
            code=RoleCode.NEUROSURGEON,
            name="신경외과",
        )
        self.neurosurgeon = User.objects.create_user(
            login_id="organization-neurosurgeon",
            password="test-password",
            name="테스트 신경외과",
            role=neurosurgeon_role,
        )
        patient_role = Role.objects.create(
            code=RoleCode.PATIENT,
            name="환자",
        )
        self.patient = User.objects.create_user(
            login_id="organization-patient",
            password="test-password",
            name="테스트 환자",
            role=patient_role,
        )
        self.hospital = Hospital.objects.create(
            name="테스트 병원",
            address="테스트 주소",
        )
        self.department = Department.objects.create(
            hospital=self.hospital,
            code="NEUROLOGY",
            name="신경과",
        )
        self.clinician = Clinician.objects.create(
            user=self.neurologist,
            department=self.department,
            is_active=True,
        )
        self.client.force_authenticate(self.nurse)

    def test_nurse_can_list_hospital_departments(self):
        response = self.client.get(
            reverse("hospital-departments", args=[self.hospital.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["departments"][0]["id"], self.department.id)

    def test_nurse_can_list_department_clinicians(self):
        response = self.client.get(
            reverse("department-clinicians", args=[self.department.id])
        )

        self.assertEqual(response.status_code, 200)
        item = response.data["clinicians"][0]
        self.assertEqual(item["id"], self.clinician.id)
        self.assertEqual(item["user_id"], self.clinician.user_id)

    def test_doctors_can_list_department_clinicians(self):
        for doctor in (self.neurologist, self.neurosurgeon):
            with self.subTest(role=doctor.role.code):
                self.client.force_authenticate(doctor)

                response = self.client.get(
                    reverse(
                        "department-clinicians",
                        args=[self.department.id],
                    )
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.data["clinicians"][0]["id"],
                    self.clinician.id,
                )

    def test_patient_can_still_list_department_clinicians(self):
        self.client.force_authenticate(self.patient)

        response = self.client.get(
            reverse("department-clinicians", args=[self.department.id])
        )

        self.assertEqual(response.status_code, 200)
