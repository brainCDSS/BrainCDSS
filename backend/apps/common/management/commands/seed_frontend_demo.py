from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, time, timedelta
from decimal import Decimal

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction
from django.utils import timezone


PASSWORD = "test1234"

NS = uuid.UUID(
    "f281c28f-9084-4c02-b012-3b8ee73cf401"
)


USERS = [
    (
        "neuro01",
        "신경과 김도현",
        ["NEUROLOGIST"],
        "NEUROLOGY",
    ),
    (
        "neuro02",
        "신경과 이서준",
        ["NEUROLOGIST"],
        "NEUROLOGY",
    ),
    (
        "neuro03",
        "신경과 박지훈",
        ["NEUROLOGIST"],
        "NEUROLOGY",
    ),

    (
        "neurosurgery01",
        "신경외과 최민석",
        ["NEUROSURGEON"],
        "NEUROSURGERY",
    ),
    (
        "neurosurgery02",
        "신경외과 정우진",
        ["NEUROSURGEON"],
        "NEUROSURGERY",
    ),
    (
        "neurosurgery03",
        "신경외과 한성민",
        ["NEUROSURGEON"],
        "NEUROSURGERY",
    ),

    (
        "radiology01",
        "영상의학과 윤지호",
        ["RADIOLOGY", "RADIOLOGIST"],
        "RADIOLOGY",
    ),
    (
        "radiology02",
        "영상의학과 김하늘",
        ["RADIOLOGY", "RADIOLOGIST"],
        "RADIOLOGY",
    ),
    (
        "radiology03",
        "영상의학과 오세진",
        ["RADIOLOGY", "RADIOLOGIST"],
        "RADIOLOGY",
    ),

    (
        "nurse01",
        "간호사 이수빈",
        ["NURSE"],
        "NURSING",
    ),
    (
        "admin01",
        "시스템 관리자",
        ["SYSTEM_ADMIN"],
        "ADMIN",
    ),
]


PATIENTS = [
    (
        "FT-I001",
        "김민준",
        date(1958, 3, 11),
        "M",
        "뇌경색",
        "I63.9",
        "neuro01",
    ),
    (
        "FT-I002",
        "이정수",
        date(1962, 7, 22),
        "M",
        "뇌경색",
        "I63.9",
        "neuro02",
    ),
    (
        "FT-I003",
        "박성호",
        date(1967, 1, 18),
        "M",
        "뇌경색",
        "I63.9",
        "neuro03",
    ),
    (
        "FT-I004",
        "최영철",
        date(1954, 10, 5),
        "M",
        "뇌경색",
        "I63.9",
        "neuro01",
    ),
    (
        "FT-I005",
        "정미경",
        date(1964, 4, 30),
        "F",
        "뇌경색",
        "I63.9",
        "neuro02",
    ),

    (
        "FT-H001",
        "강현수",
        date(1956, 2, 14),
        "M",
        "뇌출혈",
        "I61.9",
        "neurosurgery01",
    ),
    (
        "FT-H002",
        "윤정희",
        date(1960, 9, 8),
        "F",
        "뇌출혈",
        "I61.9",
        "neurosurgery02",
    ),
    (
        "FT-H003",
        "한동욱",
        date(1952, 6, 19),
        "M",
        "뇌출혈",
        "I61.9",
        "neurosurgery03",
    ),
    (
        "FT-H004",
        "조미영",
        date(1965, 11, 3),
        "F",
        "뇌출혈",
        "I61.9",
        "neurosurgery01",
    ),
    (
        "FT-H005",
        "임재훈",
        date(1959, 5, 27),
        "M",
        "뇌출혈",
        "I61.9",
        "neurosurgery02",
    ),

    (
        "FT-A001",
        "송유진",
        date(1971, 8, 12),
        "F",
        "뇌동맥류",
        "I67.1",
        "neurosurgery01",
    ),
    (
        "FT-A002",
        "오지현",
        date(1968, 12, 1),
        "F",
        "뇌동맥류",
        "I67.1",
        "neurosurgery02",
    ),
    (
        "FT-A003",
        "문수진",
        date(1974, 5, 16),
        "F",
        "뇌동맥류",
        "I67.1",
        "neurosurgery03",
    ),
    (
        "FT-A004",
        "장혜진",
        date(1966, 3, 25),
        "F",
        "뇌동맥류",
        "I67.1",
        "neurosurgery01",
    ),
    (
        "FT-A005",
        "서은경",
        date(1972, 7, 9),
        "F",
        "뇌동맥류",
        "I67.1",
        "neurosurgery02",
    ),
]


DEPTS = {
    "NEUROLOGY": (
        "FT-NEURO",
        "신경과",
    ),
    "NEUROSURGERY": (
        "FT-NS",
        "신경외과",
    ),
    "RADIOLOGY": (
        "FT-RAD",
        "영상의학과",
    ),
    "NURSING": (
        "FT-NUR",
        "간호부",
    ),
    "ADMIN": (
        "FT-ADM",
        "시스템관리",
    ),
}


def gm(app_label, model_name):
    try:
        return apps.get_model(
            app_label,
            model_name,
        )
    except LookupError:
        return None


def fmap(model):
    result = {}

    for field in model._meta.fields:
        result[field.name] = field
        result[field.attname] = field

    return result


def choice(field, *preferred):
    try:
        values = [
            value
            for value, _ in field.flatchoices
            if value not in (None, "")
        ]
    except Exception:
        values = []

    if values:
        for value in preferred:
            if value in values:
                return value

        return values[0]

    return next(
        (
            value
            for value in preferred
            if value is not None
        ),
        None,
    )


def duid(key):
    return uuid.uuid5(
        NS,
        key,
    )


class Command(BaseCommand):
    help = (
        "Frontend integration synthetic demo data seed"
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--check-only",
            action="store_true",
        )

    def handle(
        self,
        *args,
        **options,
    ):
        self.load_models()

        self.preflight()

        if options["check_only"]:
            self.stdout.write(
                self.style.SUCCESS(
                    "FRONTEND DEMO PREFLIGHT: PASS"
                )
            )
            return

        self.stats = defaultdict(int)

        with transaction.atomic():
            self.create_org_depts()

            self.create_users()

            for sequence, row in enumerate(
                PATIENTS,
                1,
            ):
                self.create_case(
                    sequence,
                    row,
                )

            self.verify()

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "======================================"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "FRONTEND DEMO SEED: PASS"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "======================================"
            )
        )

        self.stdout.write(
            "USERS   : 11"
        )
        self.stdout.write(
            "PATIENTS: 15"
        )
        self.stdout.write(
            "PASSWORD: test1234"
        )

    def load_models(self):
        self.Role = gm(
            "accounts",
            "Role",
        )

        self.User = gm(
            "accounts",
            "User",
        )

        self.Organization = gm(
            "organizations",
            "Organization",
        )

        self.Department = gm(
            "organizations",
            "Department",
        )

        self.Patient = gm(
            "patients",
            "Patient",
        )

        self.AppointmentSlot = gm(
            "appointments",
            "AppointmentSlot",
        )

        self.Appointment = gm(
            "appointments",
            "Appointment",
        )

        self.Encounter = gm(
            "clinical_records",
            "Encounter",
        )

    def preflight(self):
        required = [
            (
                "accounts.Role",
                self.Role,
            ),
            (
                "accounts.User",
                self.User,
            ),
            (
                "patients.Patient",
                self.Patient,
            ),
            (
                "appointments.AppointmentSlot",
                self.AppointmentSlot,
            ),
            (
                "appointments.Appointment",
                self.Appointment,
            ),
            (
                "clinical_records.Encounter",
                self.Encounter,
            ),
        ]

        missing = [
            name
            for name, model
            in required
            if model is None
        ]

        if missing:
            raise CommandError(
                "필수 Model 없음: "
                + ", ".join(missing)
            )

        role_fields = fmap(
            self.Role
        )

        if "code" in role_fields:
            self.role_field = "code"

        elif "role_code" in role_fields:
            self.role_field = "role_code"

        else:
            raise CommandError(
                "Role code field 없음"
            )

        for (
            login,
            _,
            role_codes,
            _,
        ) in USERS:

            found = False

            for role_code in role_codes:
                if self.Role.objects.filter(
                    **{
                        self.role_field:
                            role_code
                    }
                ).exists():
                    found = True
                    break

            if not found:
                raise CommandError(
                    f"Role 없음: "
                    f"{login} "
                    f"{role_codes}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                "PREFLIGHT: PASS"
            )
        )

    def scalar(
        self,
        field,
        key,
    ):
        selected = choice(
            field
        )

        if selected is not None:
            return selected

        name = field.name.lower()

        if isinstance(
            field,
            models.UUIDField,
        ):
            return duid(
                f"{key}:{field.name}"
            )

        if isinstance(
            field,
            models.BooleanField,
        ):
            return True

        if isinstance(
            field,
            models.DateTimeField,
        ):
            return timezone.now()

        if isinstance(
            field,
            models.DateField,
        ):
            return date.today()

        if isinstance(
            field,
            models.TimeField,
        ):
            return time(
                9,
                0,
            )

        if isinstance(
            field,
            models.DurationField,
        ):
            return timedelta(
                minutes=30
            )

        if isinstance(
            field,
            models.DecimalField,
        ):
            return Decimal("1")

        if isinstance(
            field,
            models.FloatField,
        ):
            return 1.0

        if isinstance(
            field,
            (
                models.IntegerField,
                models.BigIntegerField,
                models.SmallIntegerField,
            ),
        ):
            if (
                "count" in name
                or "retry" in name
            ):
                return 0

            return 1

        if isinstance(
            field,
            models.JSONField,
        ):
            return {}

        if isinstance(
            field,
            models.EmailField,
        ):
            return (
                f"{duid(key).hex[:12]}"
                "@brainon.test"
            )

        if isinstance(
            field,
            models.URLField,
        ):
            return (
                "https://brainon.test/demo"
            )

        if isinstance(
            field,
            models.GenericIPAddressField,
        ):
            return "127.0.0.1"

        if (
            field.get_internal_type()
            == "ArrayField"
        ):
            return []

        if isinstance(
            field,
            (
                models.CharField,
                models.TextField,
            ),
        ):
            if "email" in name:
                value = (
                    f"{duid(key).hex[:12]}"
                    "@brainon.test"
                )

            elif "phone" in name:
                value = (
                    "010"
                    + duid(key).hex[:8]
                )

            elif "status" in name:
                value = "ACTIVE"

            elif (
                "code" in name
                or "number" in name
                or name.endswith("_no")
            ):
                value = (
                    "FT-"
                    + duid(
                        f"{key}:{field.name}"
                    ).hex[:12].upper()
                )

            else:
                value = (
                    f"Frontend Demo {key}"
                )

            if getattr(
                field,
                "max_length",
                None,
            ):
                value = value[
                    :field.max_length
                ]

            return value

        if getattr(
            field,
            "empty_strings_allowed",
            False,
        ):
            return ""

        raise CommandError(
            "자동값 불가: "
            f"{field.model._meta.label}."
            f"{field.name}"
        )

    def put(
        self,
        model,
        data,
        names,
        value,
    ):
        fields = fmap(
            model
        )

        for name in names:
            field = fields.get(
                name
            )

            if field is None:
                continue

            key = (
                field.attname
                if field.is_relation
                else field.name
            )

            if (
                field.is_relation
                and hasattr(
                    value,
                    "pk",
                )
            ):
                data[key] = value.pk
            else:
                data[key] = value

            return True

        return False

    def status(
        self,
        model,
        data,
        *preferred,
    ):
        field = fmap(
            model
        ).get(
            "status"
        )

        if field:
            data["status"] = choice(
                field,
                *preferred,
            )

    def resolve_fk(
        self,
        related,
        context,
        key,
        stack,
    ):
        if (
            related in context
            and context[related]
            is not None
        ):
            return context[
                related
            ]

        existing = (
            related.objects
            .first()
        )

        if existing is not None:
            return existing

        if related in stack:
            raise CommandError(
                "FK cycle: "
                + related._meta.label
            )

        return self.upsert(
            related,
            (
                f"{key}:fk:"
                f"{related._meta.label}"
            ),
            {},
            context,
            stack + [related],
        )

    def upsert(
        self,
        model,
        key,
        values=None,
        context=None,
        stack=None,
    ):
        values = values or {}
        context = context or {}
        stack = stack or [model]

        fields = fmap(
            model
        )

        data = {}

        for name, value in (
            values.items()
        ):
            field = fields.get(
                name
            )

            if field is None:
                continue

            target = (
                field.attname
                if field.is_relation
                else field.name
            )

            if (
                field.is_relation
                and hasattr(
                    value,
                    "pk",
                )
            ):
                data[target] = (
                    value.pk
                )
            else:
                data[target] = value

        pk_field = model._meta.pk
        pk_value = None

        if isinstance(
            pk_field,
            models.UUIDField,
        ):
            pk_value = duid(
                f"{model._meta.label}:{key}"
            )

            data[
                pk_field.attname
            ] = pk_value

        for field in (
            model._meta.fields
        ):
            if field.primary_key:
                continue

            if (
                field.name in data
                or field.attname in data
            ):
                continue

            if (
                field.null
                or field.has_default()
                or getattr(
                    field,
                    "auto_now",
                    False,
                )
                or getattr(
                    field,
                    "auto_now_add",
                    False,
                )
            ):
                continue

            if field.is_relation:
                obj = self.resolve_fk(
                    field.remote_field.model,
                    context,
                    (
                        f"{key}:"
                        f"{field.name}"
                    ),
                    stack,
                )

                data[
                    field.attname
                ] = obj.pk

            else:
                data[
                    field.name
                ] = self.scalar(
                    field,
                    key,
                )

        obj = None

        if pk_value is not None:
            obj = (
                model.objects
                .filter(
                    pk=pk_value
                )
                .first()
            )

        if obj is None:
            for field in (
                model._meta.fields
            ):
                if not field.unique:
                    continue

                field_name = (
                    field.attname
                    if field.is_relation
                    else field.name
                )

                if (
                    field_name in data
                    and data[field_name]
                    is not None
                ):
                    obj = (
                        model.objects
                        .filter(
                            **{
                                field_name:
                                    data[
                                        field_name
                                    ]
                            }
                        )
                        .first()
                    )

                    if obj:
                        break

        if obj is None:
            obj = model.objects.create(
                **data
            )

            self.stats[
                model._meta.label
            ] += 1

        else:
            for name, value in (
                data.items()
            ):
                if name == (
                    pk_field.attname
                ):
                    continue

                setattr(
                    obj,
                    name,
                    value,
                )

            obj.save()

        return obj

    def role(
        self,
        role_codes,
    ):
        for role_code in role_codes:
            obj = (
                self.Role.objects
                .filter(
                    **{
                        self.role_field:
                            role_code
                    }
                )
                .first()
            )

            if obj:
                return obj

        raise CommandError(
            f"Role 없음: {role_codes}"
        )

    def create_org_depts(self):
        self.org = None
        self.depts = {}

        if self.Organization:
            values = {}

            self.put(
                self.Organization,
                values,
                (
                    "code",
                    "organization_code",
                ),
                "FT-HOSPITAL",
            )

            self.put(
                self.Organization,
                values,
                (
                    "name",
                    "organization_name",
                ),
                "BrainOn 테스트병원",
            )

            self.put(
                self.Organization,
                values,
                ("is_active",),
                True,
            )

            self.org = self.upsert(
                self.Organization,
                "org",
                values,
            )

        if self.Department:
            for (
                key,
                (
                    code,
                    name,
                ),
            ) in DEPTS.items():

                values = {}

                if self.org:
                    self.put(
                        self.Department,
                        values,
                        ("organization",),
                        self.org,
                    )

                self.put(
                    self.Department,
                    values,
                    (
                        "code",
                        "department_code",
                    ),
                    code,
                )

                self.put(
                    self.Department,
                    values,
                    (
                        "name",
                        "department_name",
                    ),
                    name,
                )

                self.put(
                    self.Department,
                    values,
                    ("is_active",),
                    True,
                )

                context = {}

                if self.org:
                    context[
                        self.Organization
                    ] = self.org

                self.depts[
                    key
                ] = self.upsert(
                    self.Department,
                    f"dept:{key}",
                    values,
                    context,
                )

    def create_users(self):
        self.users = {}

        for (
            login,
            name,
            role_codes,
            dept_key,
        ) in USERS:

            role = self.role(
                role_codes
            )

            dept = self.depts.get(
                dept_key
            )

            values = {}

            self.put(
                self.User,
                values,
                ("role",),
                role,
            )

            if dept:
                self.put(
                    self.User,
                    values,
                    ("department",),
                    dept,
                )

            if self.org:
                self.put(
                    self.User,
                    values,
                    ("organization",),
                    self.org,
                )

            self.put(
                self.User,
                values,
                (
                    "login_id",
                    "username",
                ),
                login,
            )

            self.put(
                self.User,
                values,
                ("email",),
                f"{login}@brainon.test",
            )

            self.put(
                self.User,
                values,
                (
                    "name",
                    "full_name",
                    "display_name",
                ),
                name,
            )

            self.put(
                self.User,
                values,
                ("is_active",),
                True,
            )

            self.put(
                self.User,
                values,
                ("is_staff",),
                login == "admin01",
            )

            self.put(
                self.User,
                values,
                ("is_superuser",),
                login == "admin01",
            )

            context = {
                self.Role:
                    role,
            }

            if (
                self.Department
                and dept
            ):
                context[
                    self.Department
                ] = dept

            if (
                self.Organization
                and self.org
            ):
                context[
                    self.Organization
                ] = self.org

            user = self.upsert(
                self.User,
                f"user:{login}",
                values,
                context,
            )

            user.set_password(
                PASSWORD
            )

            user.save(
                update_fields=[
                    "password"
                ]
            )

            self.users[
                login
            ] = user

        self.stdout.write(
            self.style.SUCCESS(
                "USERS: 11/11"
            )
        )

    def create_case(
        self,
        sequence,
        row,
    ):
        (
            patient_no,
            patient_name,
            birth_date,
            sex,
            disease,
            diagnosis_code,
            doctor_login,
        ) = row

        doctor = self.users[
            doctor_login
        ]

        if doctor_login.startswith(
            "neuro0"
        ):
            dept_key = "NEUROLOGY"
        else:
            dept_key = "NEUROSURGERY"

        department = self.depts.get(
            dept_key
        )

        context = {
            self.User:
                doctor,
        }

        if (
            self.Department
            and department
        ):
            context[
                self.Department
            ] = department

        if (
            self.Organization
            and self.org
        ):
            context[
                self.Organization
            ] = self.org

        # ----------------------------------------------------
        # Patient
        # ----------------------------------------------------

        values = {}

        self.put(
            self.Patient,
            values,
            (
                "patient_no",
                "patient_number",
                "mrn",
            ),
            patient_no,
        )

        self.put(
            self.Patient,
            values,
            (
                "name",
                "patient_name",
                "full_name",
            ),
            patient_name,
        )

        self.put(
            self.Patient,
            values,
            (
                "birth_date",
                "date_of_birth",
                "dob",
            ),
            birth_date,
        )

        patient_fields = fmap(
            self.Patient
        )

        sex_field = (
            patient_fields.get(
                "sex"
            )
            or patient_fields.get(
                "gender"
            )
        )

        if sex_field:
            values[
                sex_field.name
            ] = choice(
                sex_field,
                sex,
                (
                    "MALE"
                    if sex == "M"
                    else "FEMALE"
                ),
            )

        self.put(
            self.Patient,
            values,
            (
                "diagnosis_code",
                "primary_diagnosis_code",
            ),
            diagnosis_code,
        )

        self.put(
            self.Patient,
            values,
            (
                "diagnosis_name",
                "primary_diagnosis",
            ),
            disease,
        )

        self.status(
            self.Patient,
            values,
            "ACTIVE",
        )

        patient = self.upsert(
            self.Patient,
            f"patient:{patient_no}",
            values,
            context,
        )

        context[
            self.Patient
        ] = patient

        # ----------------------------------------------------
        # AppointmentSlot
        # ----------------------------------------------------

        start = (
            timezone.now()
            + timedelta(
                days=1,
                minutes=30 * sequence,
            )
        )

        end = (
            start
            + timedelta(
                minutes=30
            )
        )

        values = {}

        self.put(
            self.AppointmentSlot,
            values,
            (
                "doctor",
                "provider",
                "physician",
                "created_by",
            ),
            doctor,
        )

        if department:
            self.put(
                self.AppointmentSlot,
                values,
                ("department",),
                department,
            )

        slot_fields = fmap(
            self.AppointmentSlot
        )

        candidates = {
            "slot_date":
                start.date(),

            "date":
                start.date(),

            "appointment_date":
                start.date(),

            "start_at":
                start,

            "start_datetime":
                start,

            "end_at":
                end,

            "end_datetime":
                end,

            "start_time":
                start.time().replace(
                    tzinfo=None,
                    microsecond=0,
                ),

            "end_time":
                end.time().replace(
                    tzinfo=None,
                    microsecond=0,
                ),

            "is_available":
                True,

            "capacity":
                1,

            "booked_count":
                0,
        }

        for (
            field_name,
            field_value,
        ) in candidates.items():

            if field_name in slot_fields:
                self.put(
                    self.AppointmentSlot,
                    values,
                    (field_name,),
                    field_value,
                )

        self.status(
            self.AppointmentSlot,
            values,
            "AVAILABLE",
            "OPEN",
            "ACTIVE",
        )

        slot = self.upsert(
            self.AppointmentSlot,
            f"slot:{patient_no}",
            values,
            context,
        )

        context[
            self.AppointmentSlot
        ] = slot

        # ----------------------------------------------------
        # Appointment
        # ----------------------------------------------------

        values = {}

        self.put(
            self.Appointment,
            values,
            (
                "slot",
                "appointment_slot",
            ),
            slot,
        )

        self.put(
            self.Appointment,
            values,
            ("patient",),
            patient,
        )

        self.put(
            self.Appointment,
            values,
            (
                "doctor",
                "provider",
                "physician",
                "created_by",
            ),
            doctor,
        )

        if department:
            self.put(
                self.Appointment,
                values,
                ("department",),
                department,
            )

        self.status(
            self.Appointment,
            values,
            "CONFIRMED",
            "COMPLETED",
            "REQUESTED",
        )

        self.put(
            self.Appointment,
            values,
            (
                "appointment_at",
                "scheduled_at",
                "appointment_datetime",
            ),
            start,
        )

        self.put(
            self.Appointment,
            values,
            (
                "reason",
                "chief_complaint",
            ),
            disease + " 진료",
        )

        appointment = self.upsert(
            self.Appointment,
            f"appointment:{patient_no}",
            values,
            context,
        )

        context[
            self.Appointment
        ] = appointment

        # ----------------------------------------------------
        # Encounter
        # ----------------------------------------------------

        values = {}

        self.put(
            self.Encounter,
            values,
            ("patient",),
            patient,
        )

        self.put(
            self.Encounter,
            values,
            ("appointment",),
            appointment,
        )

        self.put(
            self.Encounter,
            values,
            (
                "doctor",
                "provider",
                "physician",
                "created_by",
            ),
            doctor,
        )

        if department:
            self.put(
                self.Encounter,
                values,
                ("department",),
                department,
            )

        case_index = (
            (sequence - 1) % 5
        ) + 1

        self.status(
            self.Encounter,
            values,
            (
                "IN_PROGRESS"
                if case_index <= 2
                else "COMPLETED"
            ),
            "COMPLETED",
            "IN_PROGRESS",
        )

        self.put(
            self.Encounter,
            values,
            (
                "encounter_no",
                "encounter_number",
            ),
            f"FT-ENC-{patient_no}",
        )

        self.put(
            self.Encounter,
            values,
            (
                "encounter_type",
                "type",
            ),
            (
                "EMERGENCY"
                if disease == "뇌출혈"
                else "OUTPATIENT"
            ),
        )

        self.put(
            self.Encounter,
            values,
            ("started_at",),
            timezone.now()
            - timedelta(hours=2),
        )

        self.upsert(
            self.Encounter,
            f"encounter:{patient_no}",
            values,
            context,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"PASS "
                f"{patient_no} "
                f"{patient_name} "
                f"{disease}"
            )
        )

    def verify(self):
        user_fields = fmap(
            self.User
        )

        login_field = (
            "login_id"
            if "login_id"
            in user_fields
            else "username"
        )

        for (
            login,
            _,
            _,
            _,
        ) in USERS:

            user = (
                self.User.objects
                .filter(
                    **{
                        login_field:
                            login
                    }
                )
                .first()
            )

            if (
                user is None
                or not user.check_password(
                    PASSWORD
                )
            ):
                raise CommandError(
                    f"로그인 검증 실패: "
                    f"{login}"
                )

        patient_fields = fmap(
            self.Patient
        )

        patient_field = next(
            (
                name
                for name in (
                    "patient_no",
                    "patient_number",
                    "mrn",
                )
                if name
                in patient_fields
            ),
            None,
        )

        if patient_field:
            patient_numbers = [
                row[0]
                for row in PATIENTS
            ]

            count = (
                self.Patient.objects
                .filter(
                    **{
                        f"{patient_field}__in":
                            patient_numbers
                    }
                )
                .count()
            )

            if count != 15:
                raise CommandError(
                    f"환자 검증 실패: "
                    f"{count}/15"
                )

        self.stdout.write(
            self.style.SUCCESS(
                "VERIFY USERS 11/11"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "VERIFY PATIENTS 15/15"
            )
        )
