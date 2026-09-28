from django.db import migrations, models


PERMISSIONS = (
    ("patient.read", "환자 조회", "patients", "허용된 환자의 기본/임상 정보를 조회합니다."),
    ("patient.create", "환자 등록", "patients", "환자 또는 임시 환자를 등록합니다."),
    ("patient.update", "환자 수정", "patients", "환자 기본 정보를 수정합니다."),
    ("patient.merge", "환자 병합", "patients", "임시 환자를 정식 환자와 병합합니다."),
    ("patient.identify", "환자 식별", "patients", "임시 환자의 신원을 확정합니다."),
    ("patient_allergy.read", "환자 알레르기 조회", "patients", "환자의 알레르기 정보를 조회합니다."),
    ("patient_allergy.manage", "환자 알레르기 관리", "patients", "환자의 알레르기 정보를 등록·수정합니다."),

    ("schedule.read", "진료 일정 조회", "appointments", "의료진 진료 일정을 조회합니다."),
    ("schedule.manage", "진료 일정 관리", "appointments", "의료진 진료 일정과 슬롯을 관리합니다."),
    ("appointment.request", "예약 요청", "appointments", "환자 예약을 요청합니다."),
    ("appointment.read.own", "본인 예약 조회", "appointments", "본인 예약 또는 허용된 예약 상세를 조회합니다."),
    ("appointment.read.staff", "의료진 예약 조회", "appointments", "업무 범위의 예약 요청을 조회합니다."),
    ("appointment.reschedule.own", "본인 예약 변경 요청", "appointments", "본인 예약 변경을 요청합니다."),
    ("appointment.cancel.own", "본인 예약 취소", "appointments", "본인 예약을 취소합니다."),
    ("appointment.accept", "예약 승인", "appointments", "예약 요청을 승인합니다."),
    ("appointment.reject", "예약 거절", "appointments", "예약 요청을 거절합니다."),
    ("appointment.complete", "예약 진료 완료", "appointments", "예약 진료를 완료 처리합니다."),
    ("appointment.correct", "예약 정정", "appointments", "예약 업무 상태를 정정합니다."),

    ("medication_safety.check", "처방 안전성 검사", "medication_safety", "DUR/Medication Safety 검사를 수행합니다."),

    ("notification.read", "알림 조회", "notifications", "본인 알림을 조회하고 읽음 처리합니다."),
    ("notification.preference.manage", "알림 설정 관리", "notifications", "본인의 알림 설정을 조회·변경합니다."),
    ("fcm.manage", "FCM 기기 토큰 관리", "notifications", "본인의 FCM 기기 토큰을 등록·비활성화합니다."),

    ("favorite.manage", "즐겨찾기 병원 관리", "patients", "환자의 즐겨찾기 병원을 관리합니다."),

    ("ai.job.view", "AI 분석 작업 조회", "ai_analysis", "허용 범위의 AI 분석 작업 상태를 조회합니다."),
    ("ai.job.retry", "AI 분석 재시도", "ai_analysis", "실패한 AI 분석 작업을 운영 권한으로 재시도합니다."),
    ("ai.model.view", "AI 모델 조회", "ai_analysis", "AI 모델/버전 운영 정보를 조회합니다."),
    ("ai.model.manage", "AI 모델 관리", "ai_analysis", "AI 모델/버전 운영 정보를 관리합니다."),
    ("ai.model.config.manage", "AI 모델 설정 관리", "ai_analysis", "AI 모델 설정 버전을 관리합니다."),
    ("ai.routing.manage", "AI 라우팅 관리", "ai_analysis", "AI 모델 라우팅 정책을 관리합니다."),

    ("integration.retry", "외부연동 재시도", "integrations", "실패한 외부 연동 작업을 재시도합니다."),
    ("system.health.view", "시스템 상태 조회", "system", "시스템 운영 상태를 조회합니다."),

    ("user.manage", "사용자 관리", "accounts", "관리자 사용자 계정을 조회하고 관리합니다."),
    ("role.manage", "역할 및 권한 관리", "accounts", "역할별 권한 구성을 조회하고 관리합니다."),
    ("audit_log.read", "감사 로그 조회", "audit", "보안 정책에 따라 감사 로그를 조회합니다."),
    ("dur.sync", "DUR 기준정보 동기화", "medication_safety", "의약품 안전성 기준정보 동기화를 요청합니다."),
)


ROLE_PERMISSION_CODES = {
    "PATIENT": {
        "schedule.read",
        "appointment.request",
        "appointment.read.own",
        "appointment.reschedule.own",
        "appointment.cancel.own",
        "favorite.manage",
        "notification.read",
        "notification.preference.manage",
        "fcm.manage",
        "patient_allergy.read",
    },

    "NURSE": {
        "patient.read",
        "patient.create",
        "patient.update",
        "patient.merge",
        "patient.identify",
        "patient_allergy.read",
        "patient_allergy.manage",
        "schedule.read",
        "schedule.manage",
        "appointment.read.staff",
        "appointment.read.own",
        "appointment.accept",
        "appointment.reject",
        "appointment.complete",
        "appointment.correct",
        "notification.read",
        "notification.preference.manage",
        "fcm.manage",
    },

    "NEUROLOGIST": {
        "patient.read",
        "patient_allergy.read",
        "patient_allergy.manage",
        "schedule.read",
        "schedule.manage",
        "appointment.read.staff",
        "appointment.read.own",
        "medication_safety.check",
        "notification.read",
        "notification.preference.manage",
        "fcm.manage",
        "ai.job.view",
    },

    "NEUROSURGEON": {
        "patient.read",
        "patient_allergy.read",
        "patient_allergy.manage",
        "schedule.read",
        "schedule.manage",
        "appointment.read.staff",
        "appointment.read.own",
        "medication_safety.check",
        "notification.read",
        "notification.preference.manage",
        "fcm.manage",
        "ai.job.view",
    },

    "RADIOLOGY": {
        "patient.read",
        "patient_allergy.read",
        "schedule.read",
        "schedule.manage",
        "appointment.read.staff",
        "appointment.read.own",
        "notification.read",
        "notification.preference.manage",
        "fcm.manage",
        "ai.job.view",
    },

    "SYSTEM_ADMIN": {
        "user.manage",
        "role.manage",
        "audit_log.read",
        "dur.sync",
        "ai.job.view",
        "ai.job.retry",
        "ai.model.view",
        "ai.model.manage",
        "ai.model.config.manage",
        "ai.routing.manage",
        "integration.retry",
        "system.health.view",
        "notification.read",
        "notification.preference.manage",
        "fcm.manage",
    },
}


MASTER_SOURCE_ROLES = (
    "NURSE",
    "NEUROLOGIST",
    "NEUROSURGEON",
    "RADIOLOGY",
)

ROLE_PERMISSION_CODES["MASTER"] = set().union(
    *(ROLE_PERMISSION_CODES[code] for code in MASTER_SOURCE_ROLES)
)


def seed_full_rbac(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Permission = apps.get_model("accounts", "Permission")
    RolePermission = apps.get_model("accounts", "RolePermission")

    master_role, _ = Role.objects.update_or_create(
        code="MASTER",
        defaults={
            "name": "마스터",
            "description": (
                "NURSE/NEUROLOGIST/NEUROSURGEON/RADIOLOGY "
                "통합 임상 시연 역할. SYSTEM_ADMIN/PATIENT 전용 권한은 상속하지 않음."
            ),
            "is_active": True,
        },
    )

    permissions = {}
    for code, name, domain, description in PERMISSIONS:
        permission, _ = Permission.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "domain": domain,
                "description": description,
            },
        )
        permissions[code] = permission

    for role_code, permission_codes in ROLE_PERMISSION_CODES.items():
        role = (
            master_role
            if role_code == "MASTER"
            else Role.objects.get(code=role_code)
        )

        for permission_code in sorted(permission_codes):
            RolePermission.objects.get_or_create(
                role=role,
                permission=permissions[permission_code],
            )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_seed_rbac_master"),
    ]

    operations = [
        migrations.AlterField(
            model_name="role",
            name="code",
            field=models.CharField(
                choices=[
                    ("PATIENT", "환자"),
                    ("NURSE", "간호사"),
                    ("NEUROLOGIST", "신경과"),
                    ("NEUROSURGEON", "신경외과"),
                    ("RADIOLOGY", "영상의학과"),
                    ("MASTER", "마스터"),
                    ("SYSTEM_ADMIN", "관리자"),
                ],
                max_length=40,
                unique=True,
            ),
        ),
        migrations.RunPython(
            seed_full_rbac,
            migrations.RunPython.noop,
        ),
    ]
