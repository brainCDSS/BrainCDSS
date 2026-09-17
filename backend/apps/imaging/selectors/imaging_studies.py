from django.db.models import (
    BooleanField,
    F,
    OuterRef,
    Q,
    Subquery,
    Value,
)
from django.db.models.functions import Coalesce

from apps.ai_analysis.models import (
    AIAnalysis,
    AIAnalysisResult,
)
from apps.consultations.models import Consultation
from apps.imaging.models import (
    ImagingStudy,
    NiftiArtifact,
    SeriesReference,
)
from apps.radiology.models import RadiologyReport
from apps.patients.selectors.patients import accessible_patient_ids


def _annotated_queryset():
    latest_analysis = (
        AIAnalysis.objects
        .filter(study_id=OuterRef("pk"))
        .order_by(
            "-requested_at",
            "-created_at",
            "-id",
        )
    )

    current_report = (
        RadiologyReport.objects
        .filter(
            study_id=OuterRef("pk"),
            is_current=True,
        )
        .order_by(
            "-version",
            "-updated_at",
            "-id",
        )
    )

    return (
        ImagingStudy.objects
        .select_related(
            "patient",
            "imaging_order",
            "imaging_order__encounter",
        )
        .annotate(
            latest_analysis_id=Subquery(
                latest_analysis.values("id")[:1]
            ),
            latest_analysis_status=Subquery(
                latest_analysis.values("status")[:1]
            ),
            current_report_id=Subquery(
                current_report.values("id")[:1]
            ),
            current_report_status=Subquery(
                current_report.values("status")[:1]
            ),
            current_report_critical=Coalesce(
                Subquery(
                    current_report.values(
                        "critical_finding"
                    )[:1],
                    output_field=BooleanField(),
                ),
                Value(False),
            ),
        )
    )


def scoped_imaging_studies(user):
    queryset = _annotated_queryset()

    role_code = getattr(
        getattr(user, "role", None),
        "code",
        None,
    )

    if role_code == "SYSTEM_ADMIN":
        return queryset

    # Use the same patient-level authorization boundary as Patient, AI and
    # NIfTI views.  Prototype artifacts never grant production access.
    return queryset.filter(patient_id__in=Subquery(accessible_patient_ids(user)))


def filter_imaging_studies(queryset, params):
    patient_id = params.get("patient_id")
    accession = params.get("accession_number")
    modality = params.get("modality")
    procedure_code = params.get("procedure_code")
    scan_type = params.get("scan_type")
    status = params.get("status")
    date_from = params.get("date_from")
    date_to = params.get("date_to")
    has_ai_result = params.get("has_ai_result")
    ai_status = params.get("ai_status")
    report_status = params.get("report_status")

    if patient_id:
        queryset = queryset.filter(
            patient_id=patient_id
        )

    if accession:
        queryset = queryset.filter(
            accession_number__icontains=accession
        )

    if modality:
        queryset = queryset.filter(
            modalities__contains=[modality]
        )

    if procedure_code:
        queryset = queryset.filter(
            imaging_order__procedure_code__iexact=
            procedure_code
        )

    if scan_type:
        queryset = queryset.filter(
            Q(
                imaging_order__procedure_code__icontains=
                scan_type
            )
            | Q(
                imaging_order__procedure_name__icontains=
                scan_type
            )
        )

    if status:
        queryset = queryset.filter(status=status)

    if date_from:
        queryset = queryset.filter(
            study_datetime__date__gte=date_from
        )

    if date_to:
        queryset = queryset.filter(
            study_datetime__date__lte=date_to
        )

    if has_ai_result is not None:
        if has_ai_result:
            queryset = queryset.filter(
                latest_analysis_id__isnull=False
            )
        else:
            queryset = queryset.filter(
                latest_analysis_id__isnull=True
            )

    if ai_status:
        queryset = queryset.filter(
            latest_analysis_status=ai_status
        )

    if report_status:
        queryset = queryset.filter(
            current_report_status=report_status
        )

    return queryset.order_by(
        F("study_datetime").desc(nulls_last=True),
        "-created_at",
        "-id",
    )


def get_scoped_imaging_study(
    *,
    user,
    study_id,
):
    return scoped_imaging_studies(user).get(
        pk=study_id
    )


def get_study_series(study_id):
    return (
        SeriesReference.objects
        .filter(study_id=study_id)
        .order_by(
            F("series_number").asc(
                nulls_last=True
            ),
            "id",
        )
    )


def list_study_ai_analyses(
    *,
    study_id,
    status=None,
    analysis_type=None,
):
    from django.db.models import (
        BooleanField,
        DecimalField,
        Exists,
    )

    result_qs = (
        AIAnalysisResult.objects
        .filter(
            analysis_id=OuterRef("pk")
        )
    )

    queryset = (
        AIAnalysis.objects
        .filter(
            study_id=study_id
        )
        .select_related(
            "model_version",
            "model_version__model",
        )
        .annotate(
            result_exists=Exists(
                result_qs
            ),
            result_is_positive=Subquery(
                result_qs.values(
                    "is_positive"
                )[:1],
                output_field=BooleanField(),
            ),
            result_total_volume_ml=Subquery(
                result_qs.values(
                    "total_volume_ml"
                )[:1],
                output_field=DecimalField(
                    max_digits=12,
                    decimal_places=4,
                ),
            ),
        )
    )

    if status:
        queryset = queryset.filter(
            status=status
        )

    if analysis_type:
        queryset = queryset.filter(
            analysis_type=analysis_type
        )

    return queryset.order_by(
        "-requested_at",
        "-created_at",
        "-id",
    )



def get_scoped_series(
    *,
    user,
    series_id,
):
    series = (
        SeriesReference.objects
        .select_related("study")
        .filter(pk=series_id)
        .first()
    )

    if series is None:
        return None

    allowed_study = (
        scoped_imaging_studies(user)
        .filter(pk=series.study_id)
        .exists()
    )

    if not allowed_study:
        return None

    return series


def list_derived_dicom_objects(series_id):
    from apps.imaging.models import (
        DicomObjectReference,
    )

    return (
        DicomObjectReference.objects
        .filter(
            series_id=series_id,
            object_type__in=[
                "SEG",
                "SR",
            ],
        )
        .order_by(
            "object_type",
            "sop_instance_uid",
        )
    )


def list_key_images(study_id):
    from apps.imaging.models import (
        KeyImageSelection,
    )

    return (
        KeyImageSelection.objects
        .filter(study_id=study_id)
        .select_related(
            "selected_by",
            "selected_by__role",
        )
        .order_by(
            "-selected_at",
            "-id",
        )
    )
