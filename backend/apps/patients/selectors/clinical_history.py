from django.db.models.functions import Coalesce

from apps.clinical_records.models import ClinicalNote, Encounter
from apps.imaging.models import ImagingOrder, ImagingStudy
from apps.prescriptions.models import Prescription


def clinical_history_encounters(patient):
    return (
        Encounter.objects.filter(patient=patient, status="COMPLETED")
        .select_related(
            "appointment__department",
            "appointment__clinician__user",
        )
        .annotate(visited_at=Coalesce("started_at", "arrived_at"))
        .order_by("-visited_at", "-id")
    )


def clinical_history_records(patient):
    encounters = list(clinical_history_encounters(patient))
    records = _history_related_records(encounters)
    return [_list_payload(encounter, records) for encounter in encounters]


def clinical_history_record(patient, encounter_id):
    encounter = clinical_history_encounters(patient).filter(id=encounter_id).first()
    if encounter is None:
        return None
    return _detail_payload(encounter, _history_related_records([encounter]))


def _history_related_records(encounters):
    encounter_ids = [encounter.id for encounter in encounters]
    orders = list(
        ImagingOrder.objects.filter(encounter_id__in=encounter_ids)
        .only("id", "encounter_id", "procedure_name")
        .order_by("requested_at", "id")
    )
    order_ids = [order.id for order in orders]
    studies_by_order = {}
    for study in ImagingStudy.objects.filter(imaging_order_id__in=order_ids).only(
        "imaging_order_id", "study_datetime"
    ).order_by("study_datetime", "id"):
        studies_by_order.setdefault(study.imaging_order_id, []).append(study)

    orders_by_encounter = {}
    for order in orders:
        orders_by_encounter.setdefault(order.encounter_id, []).append(order)

    opinions = {}
    for note in ClinicalNote.objects.filter(
        encounter_id__in=encounter_ids,
        status="FINAL",
    ).only("encounter_id", "clinical_opinion", "finalized_at").order_by(
        "encounter_id", "-finalized_at", "-id"
    ):
        opinions.setdefault(note.encounter_id, note.clinical_opinion)

    prescription_encounter_ids = set(
        Prescription.objects.filter(
            encounter_id__in=encounter_ids,
            status="FINAL",
        ).values_list("encounter_id", flat=True)
    )
    return {
        "orders": orders_by_encounter,
        "studies": studies_by_order,
        "opinions": opinions,
        "prescriptions": prescription_encounter_ids,
    }


def _base_payload(encounter):
    appointment = encounter.appointment
    return {
        "encounter_id": str(encounter.id),
        "visited_at": encounter.visited_at,
        "department_name": appointment.department.name if appointment else None,
        "clinician_name": appointment.clinician.user.name if appointment else None,
        "diagnosis_name": None,
    }


def _list_payload(encounter, records):
    payload = _base_payload(encounter)
    payload.update(
        {
            "exam_names": [
                order.procedure_name
                for order in records["orders"].get(encounter.id, [])
                if order.procedure_name
            ],
            "has_prescription": encounter.id in records["prescriptions"],
        }
    )
    return payload


def _detail_payload(encounter, records):
    payload = _base_payload(encounter)
    exams = []
    for order in records["orders"].get(encounter.id, []):
        study = (records["studies"].get(order.id) or [None])[0]
        exams.append(
            {
                "name": order.procedure_name,
                "exam_date": study.study_datetime if study else None,
            }
        )
    payload.update(
        {
            "exams": exams,
            "clinical_opinion": records["opinions"].get(encounter.id),
            "has_prescription": encounter.id in records["prescriptions"],
        }
    )
    return payload
