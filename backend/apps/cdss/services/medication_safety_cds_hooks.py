from __future__ import annotations

import uuid
from decimal import (
    Decimal,
    InvalidOperation,
)

from django.contrib.auth import (
    get_user_model,
)

from apps.accounts.models import (
    RolePermission,
)
from apps.medications.models import (
    Medication,
)
from apps.medication_safety.services.medication_safety import (
    MedicationSafetyError,
    check_medication_safety,
)
from apps.patients.models import (
    Patient,
)


CLINICAL_ROLES = {
    "NEUROLOGIST",
    "NEUROSURGEON",
}


class CDSHookError(Exception):
    def __init__(
        self,
        code,
        detail,
        status_code=400,
    ):
        self.code = code
        self.detail = detail
        self.status_code = status_code

        super().__init__(detail)


def _reference_uuid(
    value,
    field_name,
):
    if isinstance(value, dict):
        value = value.get(
            "reference"
        )

    text = str(
        value or ""
    ).strip()

    if not text:
        raise CDSHookError(
            "CDS_HOOK_INVALID_REQUEST",
            f"{field_name} is required.",
            400,
        )

    # Practitioner/<uuid>
    # Patient/<uuid>
    # Medication/<uuid>
    # 또는 UUID 자체를 모두 허용.
    if "/" in text:
        text = (
            text.rstrip("/")
            .split("/")[-1]
        )

    try:
        return uuid.UUID(text)

    except (
        ValueError,
        TypeError,
        AttributeError,
    ):
        raise CDSHookError(
            "CDS_HOOK_INVALID_REQUEST",
            (
                f"{field_name} must contain "
                "a valid UUID."
            ),
            400,
        )


def _validate_hook_instance(
    value,
):
    try:
        uuid.UUID(str(value))

    except (
        ValueError,
        TypeError,
        AttributeError,
    ):
        raise CDSHookError(
            "CDS_HOOK_INVALID_REQUEST",
            (
                "hookInstance must be "
                "a valid UUID."
            ),
            400,
        )


def _load_clinical_context(
    context,
):
    if not isinstance(
        context,
        dict,
    ):
        raise CDSHookError(
            "CDS_HOOK_INVALID_REQUEST",
            "context is required.",
            400,
        )

    user_id = _reference_uuid(
        context.get("userId"),
        "context.userId",
    )

    patient_id = _reference_uuid(
        context.get("patientId"),
        "context.patientId",
    )

    User = get_user_model()

    user = (
        User.objects
        .filter(
            id=user_id,
            is_active=True,
            role__code__in=(
                CLINICAL_ROLES
            ),
            role__is_active=True,
        )
        .select_related("role")
        .first()
    )

    if user is None:
        raise CDSHookError(
            "CDS_FORBIDDEN",
            (
                "Clinical user context "
                "is not permitted."
            ),
            403,
        )

    has_permission = (
        RolePermission.objects
        .filter(
            role=user.role,
            permission__code=(
                "medication_safety.check"
            ),
        )
        .exists()
    )

    if not has_permission:
        raise CDSHookError(
            "CDS_FORBIDDEN",
            (
                "Clinical user requires "
                "medication_safety.check."
            ),
            403,
        )

    patient = (
        Patient.objects
        .filter(
            id=patient_id,
            status="ACTIVE",
        )
        .first()
    )

    if patient is None:
        raise CDSHookError(
            "PATIENT_CONTEXT_NOT_FOUND",
            (
                "Active patient context "
                "was not found."
            ),
            404,
        )

    return user, patient


def _bundle_medication_requests(
    bundle,
):
    if not isinstance(
        bundle,
        dict,
    ):
        raise CDSHookError(
            "CDS_HOOK_INVALID_REQUEST",
            (
                "context.draftOrders must be "
                "a FHIR R4 Bundle."
            ),
            400,
        )

    if bundle.get(
        "resourceType"
    ) != "Bundle":
        raise CDSHookError(
            "CDS_HOOK_INVALID_REQUEST",
            (
                "draftOrders.resourceType "
                "must be Bundle."
            ),
            400,
        )

    entries = bundle.get(
        "entry",
        [],
    )

    if not isinstance(
        entries,
        list,
    ):
        raise CDSHookError(
            "CDS_HOOK_INVALID_REQUEST",
            (
                "draftOrders.entry must "
                "be a list."
            ),
            400,
        )

    resources = []

    for entry in entries:
        if not isinstance(
            entry,
            dict,
        ):
            continue

        resource = entry.get(
            "resource"
        )

        if (
            isinstance(resource, dict)
            and resource.get(
                "resourceType"
            )
            == "MedicationRequest"
        ):
            resources.append(
                resource
            )

    if not resources:
        raise CDSHookError(
            "CDS_HOOK_INVALID_REQUEST",
            (
                "draftOrders contains no "
                "MedicationRequest resources."
            ),
            400,
        )

    return resources


def _resolve_medication(
    resource,
):
    reference = resource.get(
        "medicationReference"
    )

    if isinstance(reference, dict):
        reference_value = (
            reference.get(
                "reference"
            )
        )

        if reference_value:
            medication_id = (
                _reference_uuid(
                    reference_value,
                    (
                        "MedicationRequest."
                        "medicationReference"
                    ),
                )
            )

            medication = (
                Medication.objects
                .filter(
                    id=medication_id,
                    is_active=True,
                )
                .first()
            )

            if medication:
                return medication

    codeable = resource.get(
        "medicationCodeableConcept"
    )

    if isinstance(codeable, dict):
        coding = codeable.get(
            "coding",
            [],
        )

        if isinstance(coding, list):
            for item in coding:
                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                code = str(
                    item.get(
                        "code",
                        ""
                    )
                ).strip()

                if not code:
                    continue

                medication = (
                    Medication.objects
                    .filter(
                        medication_code=code,
                        is_active=True,
                    )
                    .first()
                )

                if medication:
                    return medication

    raise CDSHookError(
        "CDS_HOOK_INVALID_REQUEST",
        (
            "MedicationRequest could not "
            "be mapped to an active "
            "BrainOn Medication."
        ),
        400,
    )


def _decimal_or_none(
    value,
):
    if value in (
        None,
        "",
    ):
        return None

    try:
        result = Decimal(
            str(value)
        )

    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ):
        return None

    if result <= 0:
        return None

    return result


def _daily_frequency(
    dosage,
):
    timing = dosage.get(
        "timing",
        {}
    )

    if not isinstance(
        timing,
        dict,
    ):
        return None

    repeat = timing.get(
        "repeat",
        {}
    )

    if not isinstance(
        repeat,
        dict,
    ):
        return None

    frequency = _decimal_or_none(
        repeat.get(
            "frequency"
        )
    )

    if frequency is None:
        return None

    period = _decimal_or_none(
        repeat.get(
            "period",
            1,
        )
    )

    if period is None:
        return None

    period_unit = str(
        repeat.get(
            "periodUnit",
            "d",
        )
    ).strip().lower()

    if period_unit in {
        "d",
        "day",
        "days",
    }:
        daily = (
            frequency
            / period
        )

    elif period_unit in {
        "h",
        "hour",
        "hours",
    }:
        daily = (
            frequency
            * Decimal("24")
            / period
        )

    else:
        return None

    integral = (
        daily.to_integral_value()
    )

    if (
        daily != integral
        or integral <= 0
    ):
        return None

    return int(integral)


def _route_value(
    dosage,
):
    route = dosage.get(
        "route"
    )

    if not isinstance(
        route,
        dict,
    ):
        return None

    text = str(
        route.get(
            "text",
            ""
        )
    ).strip()

    if text:
        return text

    coding = route.get(
        "coding",
        [],
    )

    if isinstance(coding, list):
        for item in coding:
            if not isinstance(
                item,
                dict,
            ):
                continue

            value = str(
                item.get("code")
                or item.get("display")
                or ""
            ).strip()

            if value:
                return value

    return None


def _dosage_values(
    resource,
):
    dosage_list = resource.get(
        "dosageInstruction",
        []
    )

    if (
        not isinstance(
            dosage_list,
            list,
        )
        or not dosage_list
        or not isinstance(
            dosage_list[0],
            dict,
        )
    ):
        return {
            "dose": None,
            "unit": None,
            "frequency_per_day": None,
            "route": None,
        }

    dosage = dosage_list[0]

    dose = None
    unit = None

    dose_and_rate = dosage.get(
        "doseAndRate",
        [],
    )

    if (
        isinstance(
            dose_and_rate,
            list,
        )
        and dose_and_rate
        and isinstance(
            dose_and_rate[0],
            dict,
        )
    ):
        quantity = (
            dose_and_rate[0]
            .get(
                "doseQuantity",
                {}
            )
        )

        if isinstance(
            quantity,
            dict,
        ):
            dose = _decimal_or_none(
                quantity.get(
                    "value"
                )
            )

            unit = str(
                quantity.get("code")
                or quantity.get("unit")
                or ""
            ).strip()

            if not unit:
                unit = None

    return {
        "dose": dose,
        "unit": unit,
        "frequency_per_day": (
            _daily_frequency(
                dosage
            )
        ),
        "route": (
            _route_value(
                dosage
            )
        ),
    }


def _medication_inputs(
    resources,
    *,
    hook,
):
    inputs = []
    incomplete_ids = set()

    for resource in resources:
        medication = (
            _resolve_medication(
                resource
            )
        )

        dosage = (
            _dosage_values(
                resource
            )
        )

        complete = all(
            (
                dosage["dose"]
                is not None,

                bool(
                    dosage["unit"]
                ),

                dosage[
                    "frequency_per_day"
                ]
                is not None,

                bool(
                    dosage["route"]
                ),
            )
        )

        if (
            hook == "order-sign"
            and not complete
        ):
            raise CDSHookError(
                "CDS_HOOK_INVALID_REQUEST",
                (
                    "order-sign requires "
                    "dose, unit, route and "
                    "frequency for every "
                    "MedicationRequest."
                ),
                400,
            )

        if not complete:
            incomplete_ids.add(
                str(medication.id)
            )

        # order-select는 dose/route 등이
        # 아직 결정되지 않을 수 있다.
        #
        # 기존 SafetyService는 양수 dose를 요구하므로
        # 임시 값으로 전체 비-DOSE Rule을 수행한 뒤,
        # 해당 Medication의 DOSE 결과만 제거한다.
        inputs.append(
            {
                "medication_id": (
                    medication.id
                ),
                "dose": (
                    dosage["dose"]
                    if dosage["dose"]
                    is not None
                    else Decimal("1")
                ),
                "unit": (
                    dosage["unit"]
                    or "mg"
                ),
                "frequency_per_day": (
                    dosage[
                        "frequency_per_day"
                    ]
                    or 1
                ),
                "route": (
                    dosage["route"]
                ),
            }
        )

    return (
        inputs,
        incomplete_ids,
    )


def _card_from_alert(
    alert,
):
    severity = str(
        alert.get(
            "severity",
            ""
        )
    ).upper()

    if severity == "BLOCK":
        indicator = "critical"

    elif severity in {
        "MAJOR",
        "WARNING",
    }:
        indicator = "warning"

    else:
        indicator = "info"

    alert_type = str(
        alert.get(
            "alert_type",
            "SAFETY",
        )
    )

    card = {
        "uuid": str(
            uuid.uuid4()
        ),
        "summary": (
            f"{alert_type} "
            "약물 안전성 경고"
        ),
        "detail": str(
            alert.get(
                "message",
                ""
            )
        ),
        "indicator": indicator,
        "source": {
            "label": (
                "BrainOn CDSS"
            ),
        },
        "extension": {
            "brainon": {
                "alertType": (
                    alert_type
                ),
                "severity": (
                    severity
                ),
                "ruleId": str(
                    alert.get(
                        "rule_id",
                        ""
                    )
                ),
                "relatedMedications": (
                    alert.get(
                        "related_medications",
                        [],
                    )
                ),
            }
        },
    }

    if alert.get(
        "override_allowed"
    ):
        card[
            "overrideReasons"
        ] = [
            {
                "code": (
                    alert_type
                ),
                "display": (
                    "임상적 판단에 따른 "
                    "Override"
                ),
            }
        ]

    return card


def evaluate_medication_safety_cds_hook(
    *,
    payload,
    expected_hook,
):
    if not isinstance(
        payload,
        dict,
    ):
        raise CDSHookError(
            "CDS_HOOK_INVALID_REQUEST",
            (
                "CDS Hooks request "
                "must be an object."
            ),
            400,
        )

    hook = str(
        payload.get(
            "hook",
            ""
        )
    ).strip()

    if hook != expected_hook:
        raise CDSHookError(
            "CDS_HOOK_UNSUPPORTED",
            (
                f"Expected hook "
                f"'{expected_hook}', "
                f"received '{hook}'."
            ),
            400,
        )

    _validate_hook_instance(
        payload.get(
            "hookInstance"
        )
    )

    context = payload.get(
        "context"
    )

    user, patient = (
        _load_clinical_context(
            context
        )
    )

    if expected_hook == "order-select":
        selections = context.get(
            "selections"
        )

        if not isinstance(
            selections,
            list,
        ):
            raise CDSHookError(
                "CDS_HOOK_INVALID_REQUEST",
                (
                    "order-select requires "
                    "context.selections list."
                ),
                400,
            )

    bundle = context.get(
        "draftOrders"
    )

    resources = (
        _bundle_medication_requests(
            bundle
        )
    )

    inputs, incomplete_ids = (
        _medication_inputs(
            resources,
            hook=expected_hook,
        )
    )

    try:
        result = (
            check_medication_safety(
                medications=inputs,
                patient=patient,
            )
        )

    except MedicationSafetyError as exc:
        raise CDSHookError(
            "CDS_HOOK_INVALID_REQUEST",
            (
                f"{exc.code}: "
                f"{exc.detail}"
            ),
            400,
        )

    alerts = list(
        result["alerts"]
    )

    if (
        expected_hook
        == "order-select"
        and incomplete_ids
    ):
        filtered = []

        for alert in alerts:
            if (
                alert.get(
                    "alert_type"
                )
                != "DOSE"
            ):
                filtered.append(
                    alert
                )
                continue

            related = {
                str(value)
                for value
                in alert.get(
                    "related_medications",
                    [],
                )
            }

            if not (
                related
                & incomplete_ids
            ):
                filtered.append(
                    alert
                )

        alerts = filtered

    return {
        "cards": [
            _card_from_alert(
                alert
            )
            for alert in alerts
        ]
    }
