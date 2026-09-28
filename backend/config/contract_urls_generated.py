"""
AUTO-GENERATED BrainOn final API contract routes.

Generated from:
api_contract_176.csv
"""

from django.urls import path

from apps.ai_analysis import contract_views_generated as ai_analysis_contract_views
from apps.appointments import contract_views_generated as appointments_contract_views
from apps.assessments import contract_views_generated as assessments_contract_views
from apps.audit import contract_views_generated as audit_contract_views
from apps.cdss import contract_views_generated as cdss_contract_views
from apps.clinical_records import contract_views_generated as clinical_records_contract_views
from apps.common import contract_views_generated as common_contract_views
from apps.consultations import contract_views_generated as consultations_contract_views
from apps.imaging import contract_views_generated as imaging_contract_views
from apps.integrations import contract_views_generated as integrations_contract_views
from apps.medication_safety import contract_views_generated as medication_safety_contract_views
from apps.medications import contract_views_generated as medications_contract_views
from apps.notifications import contract_views_generated as notifications_contract_views
from apps.organizations import contract_views_generated as organizations_contract_views
from apps.patients import contract_views_generated as patients_contract_views
from apps.prescriptions import contract_views_generated as prescriptions_contract_views
from apps.radiology import contract_views_generated as radiology_contract_views


urlpatterns = [
    # API-AI-001,API-AI-002
    path(
        'api/v1/ai-analyses',
        ai_analysis_contract_views.AiAnalysisContractEndpoint001View.as_view(),
        name='contract-endpoint-009',
    ),
    # API-AI-003
    path(
        'api/v1/ai-analyses/<str:analysis_id>',
        ai_analysis_contract_views.AiAnalysisContractEndpoint002View.as_view(),
        name='contract-endpoint-010',
    ),
    # API-AI-004
    path(
        'api/v1/ai-analyses/<str:analysis_id>/result',
        ai_analysis_contract_views.AiAnalysisContractEndpoint003View.as_view(),
        name='contract-endpoint-011',
    ),
    # API-AI-005
    path(
        'api/v1/ai-analyses/<str:analysis_id>/attempts',
        ai_analysis_contract_views.AiAnalysisContractEndpoint004View.as_view(),
        name='contract-endpoint-012',
    ),
    # API-AI-006
    path(
        'api/v1/ai-analyses/<str:analysis_id>/retry',
        ai_analysis_contract_views.AiAnalysisContractEndpoint005View.as_view(),
        name='contract-endpoint-013',
    ),
    # API-AI-007
    path(
        'api/v1/ai-analyses/<str:analysis_id>/cancel',
        ai_analysis_contract_views.AiAnalysisContractEndpoint006View.as_view(),
        name='contract-endpoint-014',
    ),
    # API-AI-008,API-AI-009
    path(
        'api/v1/ai-results/<str:result_id>/reviews',
        ai_analysis_contract_views.AiAnalysisContractEndpoint007View.as_view(),
        name='contract-endpoint-015',
    ),
    # API-AI-010
    path(
        'internal/v1/inference',
        ai_analysis_contract_views.AiAnalysisContractEndpoint008View.as_view(),
        name='contract-endpoint-016',
    ),
    # API-MDL-001,API-MDL-002
    path(
        'api/v1/ai-models',
        ai_analysis_contract_views.AiAnalysisContractEndpoint009View.as_view(),
        name='contract-endpoint-017',
    ),
    # API-MDL-003,API-MDL-004
    path(
        'api/v1/ai-models/<str:model_id>',
        ai_analysis_contract_views.AiAnalysisContractEndpoint010View.as_view(),
        name='contract-endpoint-018',
    ),
    # API-MDL-005,API-MDL-006
    path(
        'api/v1/ai-models/<str:model_id>/versions',
        ai_analysis_contract_views.AiAnalysisContractEndpoint011View.as_view(),
        name='contract-endpoint-019',
    ),
    # API-MDL-007
    path(
        'api/v1/ai-model-versions/<str:version_id>',
        ai_analysis_contract_views.AiAnalysisContractEndpoint012View.as_view(),
        name='contract-endpoint-020',
    ),
    # API-MDL-008
    path(
        'api/v1/ai-model-versions/<str:version_id>/activate',
        ai_analysis_contract_views.AiAnalysisContractEndpoint013View.as_view(),
        name='contract-endpoint-021',
    ),
    # API-MDL-009
    path(
        'api/v1/ai-model-versions/<str:version_id>/deactivate',
        ai_analysis_contract_views.AiAnalysisContractEndpoint014View.as_view(),
        name='contract-endpoint-022',
    ),
    # API-MDL-010
    path(
        'api/v1/ai-model-versions/<str:version_id>/metrics',
        ai_analysis_contract_views.AiAnalysisContractEndpoint015View.as_view(),
        name='contract-endpoint-023',
    ),
    # API-OPS-001
    path(
        'api/v1/operations/ai-jobs/summary',
        ai_analysis_contract_views.AiAnalysisContractEndpoint016View.as_view(),
        name='contract-endpoint-024',
    ),
    # API-MDL-011
    path(
        'api/v1/ai-model-versions/<str:version_id>/config',
        ai_analysis_contract_views.AiAnalysisContractEndpoint017View.as_view(),
        name='contract-endpoint-025',
    ),
    # API-MDL-012
    path(
        'api/v1/ai-model-versions/<str:version_id>/configs',
        ai_analysis_contract_views.AiAnalysisContractEndpoint018View.as_view(),
        name='contract-endpoint-026',
    ),
    # API-MDL-013
    path(
        'api/v1/ai-model-configs/<str:config_id>/activate',
        ai_analysis_contract_views.AiAnalysisContractEndpoint019View.as_view(),
        name='contract-endpoint-027',
    ),
    # API-MDL-014,API-MDL-015
    path(
        'api/v1/ai-routing-configs',
        ai_analysis_contract_views.AiAnalysisContractEndpoint020View.as_view(),
        name='contract-endpoint-028',
    ),
    # API-MDL-016
    path(
        'api/v1/ai-routing-configs/<str:routing_id>/activate',
        ai_analysis_contract_views.AiAnalysisContractEndpoint021View.as_view(),
        name='contract-endpoint-029',
    ),
    # API-MDL-017
    path(
        'api/v1/ai-model-versions/<str:version_id>/rollback',
        ai_analysis_contract_views.AiAnalysisContractEndpoint022View.as_view(),
        name='contract-endpoint-030',
    ),
    # API-OPS-008
    path(
        'api/v1/operations/ai-artifacts',
        ai_analysis_contract_views.AiAnalysisContractEndpoint023View.as_view(),
        name='contract-endpoint-031',
    ),
    # API-MDL-018
    path(
        'api/v1/ai-model-versions/<str:version_id>/validate',
        ai_analysis_contract_views.AiAnalysisContractEndpoint024View.as_view(),
        name='contract-endpoint-032',
    ),
    # API-MDL-019
    path(
        'api/v1/ai-model-versions/<str:version_id>/approve',
        ai_analysis_contract_views.AiAnalysisContractEndpoint025View.as_view(),
        name='contract-endpoint-033',
    ),
    # API-MDL-020
    path(
        'api/v1/ai-model-versions/<str:version_id>/retire',
        ai_analysis_contract_views.AiAnalysisContractEndpoint026View.as_view(),
        name='contract-endpoint-034',
    ),
    # API-SCH-001,API-SCH-002
    path(
        'api/v1/clinicians/<str:clinician_id>/schedule',
        appointments_contract_views.AppointmentsContractEndpoint001View.as_view(),
        name='contract-endpoint-035',
    ),
    # API-SLOT-001
    path(
        'api/v1/clinicians/<str:clinician_id>/slots',
        appointments_contract_views.AppointmentsContractEndpoint002View.as_view(),
        name='contract-endpoint-036',
    ),
    # API-SLOT-002
    path(
        'api/v1/slots/<str:slot_id>/block',
        appointments_contract_views.AppointmentsContractEndpoint003View.as_view(),
        name='contract-endpoint-037',
    ),
    # API-SLOT-003
    path(
        'api/v1/slots/<str:slot_id>/unblock',
        appointments_contract_views.AppointmentsContractEndpoint004View.as_view(),
        name='contract-endpoint-038',
    ),
    # API-APP-001,API-APP-002
    path(
        'api/v1/appointments',
        appointments_contract_views.AppointmentsContractEndpoint005View.as_view(),
        name='contract-endpoint-039',
    ),
    # API-APP-003
    path(
        'api/v1/appointments/<str:appointment_id>',
        appointments_contract_views.AppointmentsContractEndpoint006View.as_view(),
        name='contract-endpoint-040',
    ),
    # API-APP-004
    path(
        'api/v1/appointments/<str:appointment_id>/reschedule',
        appointments_contract_views.AppointmentsContractEndpoint007View.as_view(),
        name='contract-endpoint-041',
    ),
    # API-APP-005
    path(
        'api/v1/appointments/<str:appointment_id>/cancel',
        appointments_contract_views.AppointmentsContractEndpoint008View.as_view(),
        name='contract-endpoint-042',
    ),
    # API-APP-006
    path(
        'api/v1/nurse/appointments/requests',
        appointments_contract_views.AppointmentsContractEndpoint009View.as_view(),
        name='contract-endpoint-043',
    ),
    # API-APP-007
    path(
        'api/v1/appointments/<str:appointment_id>/accept',
        appointments_contract_views.AppointmentsContractEndpoint010View.as_view(),
        name='contract-endpoint-044',
    ),
    # API-APP-008
    path(
        'api/v1/appointments/<str:appointment_id>/reject',
        appointments_contract_views.AppointmentsContractEndpoint011View.as_view(),
        name='contract-endpoint-045',
    ),
    # API-APP-009
    path(
        'api/v1/staff/appointments',
        appointments_contract_views.AppointmentsContractEndpoint012View.as_view(),
        name='contract-endpoint-046',
    ),
    # API-APP-010
    path(
        'api/v1/appointments/<str:appointment_id>/complete',
        appointments_contract_views.AppointmentsContractEndpoint013View.as_view(),
        name='contract-endpoint-047',
    ),
    # API-ASM-001
    path(
        'api/v1/assessments/worklist',
        assessments_contract_views.AssessmentsContractEndpoint001View.as_view(),
        name='contract-endpoint-048',
    ),
    # API-ASM-002
    path(
        'api/v1/assessments',
        assessments_contract_views.AssessmentsContractEndpoint002View.as_view(),
        name='contract-endpoint-049',
    ),
    # API-ASM-003,API-ASM-004
    path(
        'api/v1/assessments/<str:assessment_id>',
        assessments_contract_views.AssessmentsContractEndpoint003View.as_view(),
        name='contract-endpoint-050',
    ),
    # API-ASM-005
    path(
        'api/v1/assessments/<str:assessment_id>/complete',
        assessments_contract_views.AssessmentsContractEndpoint004View.as_view(),
        name='contract-endpoint-051',
    ),
    # API-ASM-006
    path(
        'api/v1/neurology/emergency-worklist',
        assessments_contract_views.AssessmentsContractEndpoint005View.as_view(),
        name='contract-endpoint-052',
    ),
    # API-EVT-001
    path(
        'api/v1/emergency-events/<str:event_id>/acknowledge',
        assessments_contract_views.AssessmentsContractEndpoint006View.as_view(),
        name='contract-endpoint-053',
    ),
    # API-OPS-003
    path(
        'api/v1/operations/audit-logs',
        audit_contract_views.AuditContractEndpoint001View.as_view(),
        name='contract-endpoint-054',
    ),
    # API-OPS-004
    path(
        'api/v1/operations/audit-logs/<str:audit_id>',
        audit_contract_views.AuditContractEndpoint002View.as_view(),
        name='contract-endpoint-055',
    ),
    # API-CDS-001
    path(
        'cds-services',
        cdss_contract_views.CdssContractEndpoint001View.as_view(),
        name='contract-endpoint-056',
    ),
    # API-CDS-002
    path(
        'cds-services/medication-safety-order-select',
        cdss_contract_views.CdssContractEndpoint002View.as_view(),
        name='contract-endpoint-057',
    ),
    # API-CDS-003
    path(
        'cds-services/medication-safety-order-sign',
        cdss_contract_views.CdssContractEndpoint003View.as_view(),
        name='contract-endpoint-058',
    ),
    # API-CDS-004
    path(
        'cds-services/stroke-patient-view',
        cdss_contract_views.CdssContractEndpoint004View.as_view(),
        name='contract-endpoint-059',
    ),
    # API-ENC-001
    path(
        'api/v1/encounters',
        clinical_records_contract_views.ClinicalRecordsContractEndpoint001View.as_view(),
        name='contract-endpoint-060',
    ),
    # API-ENC-002
    path(
        'api/v1/encounters/<str:encounter_id>/start',
        clinical_records_contract_views.ClinicalRecordsContractEndpoint002View.as_view(),
        name='contract-endpoint-061',
    ),
    # API-ENC-003
    path(
        'api/v1/encounters/<str:encounter_id>/complete',
        clinical_records_contract_views.ClinicalRecordsContractEndpoint003View.as_view(),
        name='contract-endpoint-062',
    ),
    # API-ENC-004
    path(
        'api/v1/encounters/<str:encounter_id>/cancel',
        clinical_records_contract_views.ClinicalRecordsContractEndpoint004View.as_view(),
        name='contract-endpoint-063',
    ),
    # API-NOTE-001,API-NOTE-002
    path(
        'api/v1/clinical-notes',
        clinical_records_contract_views.ClinicalRecordsContractEndpoint005View.as_view(),
        name='contract-endpoint-064',
    ),
    # API-NOTE-003,API-NOTE-004
    path(
        'api/v1/clinical-notes/<str:note_id>',
        clinical_records_contract_views.ClinicalRecordsContractEndpoint006View.as_view(),
        name='contract-endpoint-065',
    ),
    # API-NOTE-005
    path(
        'api/v1/clinical-notes/<str:note_id>/finalize',
        clinical_records_contract_views.ClinicalRecordsContractEndpoint007View.as_view(),
        name='contract-endpoint-066',
    ),
    # API-OPS-005
    path(
        'internal/metrics',
        common_contract_views.CommonContractEndpoint001View.as_view(),
        name='contract-endpoint-067',
    ),
    # API-CON-001,API-CON-002
    path(
        'api/v1/consultations',
        consultations_contract_views.ConsultationsContractEndpoint001View.as_view(),
        name='contract-endpoint-068',
    ),
    # API-CON-003
    path(
        'api/v1/consultations/<str:consultation_id>',
        consultations_contract_views.ConsultationsContractEndpoint002View.as_view(),
        name='contract-endpoint-069',
    ),
    # API-CON-004
    path(
        'api/v1/consultations/<str:consultation_id>/accept',
        consultations_contract_views.ConsultationsContractEndpoint003View.as_view(),
        name='contract-endpoint-070',
    ),
    # API-CON-005
    path(
        'api/v1/consultations/<str:consultation_id>/start',
        consultations_contract_views.ConsultationsContractEndpoint004View.as_view(),
        name='contract-endpoint-071',
    ),
    # API-CON-006
    path(
        'api/v1/consultations/<str:consultation_id>/respond',
        consultations_contract_views.ConsultationsContractEndpoint005View.as_view(),
        name='contract-endpoint-072',
    ),
    # API-CON-007
    path(
        'api/v1/consultations/<str:consultation_id>/view-response',
        consultations_contract_views.ConsultationsContractEndpoint006View.as_view(),
        name='contract-endpoint-073',
    ),
    # API-CON-008
    path(
        'api/v1/consultations/<str:consultation_id>/reject',
        consultations_contract_views.ConsultationsContractEndpoint007View.as_view(),
        name='contract-endpoint-074',
    ),
    # API-CON-009
    path(
        'api/v1/consultations/<str:consultation_id>/cancel',
        consultations_contract_views.ConsultationsContractEndpoint008View.as_view(),
        name='contract-endpoint-075',
    ),
    # API-IMG-001,API-IMG-012
    path(
        'api/v1/imaging-orders',
        imaging_contract_views.ImagingContractEndpoint001View.as_view(),
        name='contract-endpoint-076',
    ),
    # API-IMG-002,API-IMG-013
    path(
        'api/v1/imaging-orders/<str:order_id>',
        imaging_contract_views.ImagingContractEndpoint002View.as_view(),
        name='contract-endpoint-077',
    ),
    # API-IMG-003
    path(
        'api/v1/imaging-studies',
        imaging_contract_views.ImagingContractEndpoint003View.as_view(),
        name='contract-endpoint-078',
    ),
    # API-IMG-004
    path(
        'api/v1/imaging-studies/<str:study_id>',
        imaging_contract_views.ImagingContractEndpoint004View.as_view(),
        name='contract-endpoint-079',
    ),
    # API-IMG-005
    path(
        'api/v1/imaging-studies/<str:study_id>/series',
        imaging_contract_views.ImagingContractEndpoint005View.as_view(),
        name='contract-endpoint-080',
    ),
    # API-IMG-006
    path(
        'api/v1/imaging-series/<str:series_id>',
        imaging_contract_views.ImagingContractEndpoint006View.as_view(),
        name='contract-endpoint-081',
    ),
    # API-IMG-007
    path(
        'api/v1/imaging-studies/<str:study_id>/viewer-session',
        imaging_contract_views.ImagingContractEndpoint007View.as_view(),
        name='contract-endpoint-082',
    ),
    # API-IMG-008
    path(
        'api/v1/imaging-studies/<str:study_id>/resync',
        imaging_contract_views.ImagingContractEndpoint008View.as_view(),
        name='contract-endpoint-083',
    ),
    # API-IMG-009
    path(
        'api/v1/imaging-studies/<str:study_id>/ai-analyses',
        imaging_contract_views.ImagingContractEndpoint009View.as_view(),
        name='contract-endpoint-084',
    ),
    # API-IMG-010
    path(
        'api/v1/imaging-studies/<str:study_id>/reports',
        imaging_contract_views.ImagingContractEndpoint010View.as_view(),
        name='contract-endpoint-085',
    ),
    # API-IMG-011
    path(
        'internal/v1/orthanc/events/stable-study',
        imaging_contract_views.ImagingContractEndpoint011View.as_view(),
        name='contract-endpoint-086',
    ),
    # API-DICOM-001
    path(
        'dicom-web/studies/<str:study_instance_uid>/series',
        imaging_contract_views.ImagingContractEndpoint012View.as_view(),
        name='contract-endpoint-087',
    ),
    # API-DICOM-002
    path(
        'api/v1/imaging-studies/<str:study_id>/viewer-context',
        imaging_contract_views.ImagingContractEndpoint013View.as_view(),
        name='contract-endpoint-088',
    ),
    # API-DICOM-003
    path(
        'internal/v1/dicom/artifacts/stow',
        imaging_contract_views.ImagingContractEndpoint014View.as_view(),
        name='contract-endpoint-089',
    ),
    # API-IMG-014
    path(
        'api/v1/imaging-orders/<str:order_id>/cancel',
        imaging_contract_views.ImagingContractEndpoint015View.as_view(),
        name='contract-endpoint-090',
    ),
    # API-IMG-015
    path(
        'api/v1/imaging-orders/<str:order_id>/timeline',
        imaging_contract_views.ImagingContractEndpoint016View.as_view(),
        name='contract-endpoint-091',
    ),
    # API-IMG-016
    path(
        'internal/v1/imaging-orders/<str:order_id>/status-events',
        imaging_contract_views.ImagingContractEndpoint017View.as_view(),
        name='contract-endpoint-092',
    ),
    # API-IMG-017
    path(
        'api/v1/imaging-reconciliation-tasks',
        imaging_contract_views.ImagingContractEndpoint018View.as_view(),
        name='contract-endpoint-093',
    ),
    # API-IMG-018
    path(
        'api/v1/imaging-reconciliation-tasks/<str:task_id>/resolve',
        imaging_contract_views.ImagingContractEndpoint019View.as_view(),
        name='contract-endpoint-094',
    ),
    # API-IMG-019
    path(
        'api/v1/dicom-transfer-jobs/<str:job_id>/retry',
        imaging_contract_views.ImagingContractEndpoint020View.as_view(),
        name='contract-endpoint-095',
    ),
    # API-IMG-020,API-IMG-021
    path(
        'api/v1/imaging-studies/<str:study_id>/key-images',
        imaging_contract_views.ImagingContractEndpoint021View.as_view(),
        name='contract-endpoint-096',
    ),
    # API-FHIR-001
    path(
        'fhir/R4/metadata',
        integrations_contract_views.IntegrationsContractEndpoint001View.as_view(),
        name='contract-endpoint-097',
    ),
    # API-FHIR-002
    path(
        'fhir/R4/Patient/<str:id>',
        integrations_contract_views.IntegrationsContractEndpoint002View.as_view(),
        name='contract-endpoint-098',
    ),
    # API-FHIR-003
    path(
        'fhir/R4/Patient',
        integrations_contract_views.IntegrationsContractEndpoint003View.as_view(),
        name='contract-endpoint-099',
    ),
    # API-FHIR-004
    path(
        'fhir/R4/ImagingStudy/<str:id>',
        integrations_contract_views.IntegrationsContractEndpoint004View.as_view(),
        name='contract-endpoint-100',
    ),
    # API-FHIR-005
    path(
        'fhir/R4/ImagingStudy',
        integrations_contract_views.IntegrationsContractEndpoint005View.as_view(),
        name='contract-endpoint-101',
    ),
    # API-FHIR-006
    path(
        'fhir/R4/DiagnosticReport/<str:id>',
        integrations_contract_views.IntegrationsContractEndpoint006View.as_view(),
        name='contract-endpoint-102',
    ),
    # API-FHIR-007
    path(
        'fhir/R4/DiagnosticReport',
        integrations_contract_views.IntegrationsContractEndpoint007View.as_view(),
        name='contract-endpoint-103',
    ),
    # API-FHIR-008
    path(
        'fhir/R4/Observation',
        integrations_contract_views.IntegrationsContractEndpoint008View.as_view(),
        name='contract-endpoint-104',
    ),
    # API-FHIR-009
    path(
        'fhir/R4/MedicationRequest',
        integrations_contract_views.IntegrationsContractEndpoint009View.as_view(),
        name='contract-endpoint-105',
    ),
    # API-FHIR-010
    path(
        'fhir/R4/Appointment',
        integrations_contract_views.IntegrationsContractEndpoint010View.as_view(),
        name='contract-endpoint-106',
    ),
    # API-HL7-001
    path(
        'api/v1/integration/hl7/adt',
        integrations_contract_views.IntegrationsContractEndpoint011View.as_view(),
        name='contract-endpoint-107',
    ),
    # API-HL7-002
    path(
        'api/v1/integration/hl7/orm',
        integrations_contract_views.IntegrationsContractEndpoint012View.as_view(),
        name='contract-endpoint-108',
    ),
    # API-HL7-003
    path(
        'api/v1/integration/hl7/oru',
        integrations_contract_views.IntegrationsContractEndpoint013View.as_view(),
        name='contract-endpoint-109',
    ),
    # API-INT-001
    path(
        'api/v1/integration/messages',
        integrations_contract_views.IntegrationsContractEndpoint014View.as_view(),
        name='contract-endpoint-110',
    ),
    # API-INT-002
    path(
        'api/v1/integration/messages/<str:message_id>',
        integrations_contract_views.IntegrationsContractEndpoint015View.as_view(),
        name='contract-endpoint-111',
    ),
    # API-INT-003
    path(
        'api/v1/integration/messages/<str:message_id>/reprocess',
        integrations_contract_views.IntegrationsContractEndpoint016View.as_view(),
        name='contract-endpoint-112',
    ),
    # API-OPS-002
    path(
        'api/v1/operations/integrations/summary',
        integrations_contract_views.IntegrationsContractEndpoint017View.as_view(),
        name='contract-endpoint-113',
    ),
    # API-MEDSAFE-001
    path(
        'api/v1/prescriptions/safety-check',
        medication_safety_contract_views.MedicationSafetyContractEndpoint001View.as_view(),
        name='contract-endpoint-114',
    ),
    # API-ALLERGY-001,API-ALLERGY-002
    path(
        'api/v1/patients/<str:patient_id>/allergies',
        medication_safety_contract_views.MedicationSafetyContractEndpoint002View.as_view(),
        name='contract-endpoint-115',
    ),
    # API-ALLERGY-003
    path(
        'api/v1/patients/<str:patient_id>/allergies/<str:allergy_id>',
        medication_safety_contract_views.MedicationSafetyContractEndpoint003View.as_view(),
        name='contract-endpoint-116',
    ),
    # API-DUR-001
    path(
        'api/v1/admin/dur/sync',
        medication_safety_contract_views.MedicationSafetyContractEndpoint004View.as_view(),
        name='contract-endpoint-117',
    ),
    # API-MEDM-001
    path(
        'api/v1/medications',
        medications_contract_views.MedicationsContractEndpoint001View.as_view(),
        name='contract-endpoint-118',
    ),
    # API-MEDM-002
    path(
        'api/v1/medications/<str:medication_id>',
        medications_contract_views.MedicationsContractEndpoint002View.as_view(),
        name='contract-endpoint-119',
    ),
    # API-MED-001
    path(
        'api/v1/medication-schedules',
        medications_contract_views.MedicationsContractEndpoint003View.as_view(),
        name='contract-endpoint-120',
    ),
    # API-MED-002
    path(
        'api/v1/medication-intakes',
        medications_contract_views.MedicationsContractEndpoint004View.as_view(),
        name='contract-endpoint-121',
    ),
    # API-MED-003
    path(
        'api/v1/medication-intakes/<str:intake_id>',
        medications_contract_views.MedicationsContractEndpoint005View.as_view(),
        name='contract-endpoint-122',
    ),
    # API-NOTI-001
    path(
        'api/v1/notifications',
        notifications_contract_views.NotificationsContractEndpoint001View.as_view(),
        name='contract-endpoint-123',
    ),
    # API-NOTI-002
    path(
        'api/v1/notifications/<str:notification_id>/read',
        notifications_contract_views.NotificationsContractEndpoint002View.as_view(),
        name='contract-endpoint-124',
    ),
    # API-NOTI-003,API-NOTI-004
    path(
        'api/v1/notification-preferences',
        notifications_contract_views.NotificationsContractEndpoint003View.as_view(),
        name='contract-endpoint-125',
    ),
    # API-FCM-001
    path(
        'api/v1/devices/fcm-tokens',
        notifications_contract_views.NotificationsContractEndpoint004View.as_view(),
        name='contract-endpoint-126',
    ),
    # API-FCM-002
    path(
        'api/v1/devices/fcm-tokens/<str:token_id>',
        notifications_contract_views.NotificationsContractEndpoint005View.as_view(),
        name='contract-endpoint-127',
    ),
    # API-REF-001
    path(
        'api/v1/hospitals',
        organizations_contract_views.OrganizationsContractEndpoint001View.as_view(),
        name='contract-endpoint-128',
    ),
    # API-REF-002
    path(
        'api/v1/hospitals/<str:hospital_id>',
        organizations_contract_views.OrganizationsContractEndpoint002View.as_view(),
        name='contract-endpoint-129',
    ),
    # API-REF-003
    path(
        'api/v1/hospitals/<str:hospital_id>/departments',
        organizations_contract_views.OrganizationsContractEndpoint003View.as_view(),
        name='contract-endpoint-130',
    ),
    # API-REF-004
    path(
        'api/v1/departments/<str:department_id>/clinicians',
        organizations_contract_views.OrganizationsContractEndpoint004View.as_view(),
        name='contract-endpoint-131',
    ),
    # API-PAT-001,API-PAT-002
    path(
        'api/v1/patients',
        patients_contract_views.PatientsContractEndpoint001View.as_view(),
        name='contract-endpoint-132',
    ),
    # API-PAT-003
    path(
        'api/v1/patients/temporary',
        patients_contract_views.PatientsContractEndpoint002View.as_view(),
        name='contract-endpoint-133',
    ),
    # API-PAT-004,API-PAT-005
    path(
        'api/v1/patients/<str:patient_id>',
        patients_contract_views.PatientsContractEndpoint003View.as_view(),
        name='contract-endpoint-134',
    ),
    # API-PAT-006
    path(
        'api/v1/patients/<str:temp_patient_id>/merge',
        patients_contract_views.PatientsContractEndpoint004View.as_view(),
        name='contract-endpoint-135',
    ),
    # API-PAT-007
    path(
        'api/v1/patients/<str:patient_id>/identify',
        patients_contract_views.PatientsContractEndpoint005View.as_view(),
        name='contract-endpoint-136',
    ),
    # API-FAV-001
    path(
        'api/v1/me/favorite-hospitals',
        patients_contract_views.PatientsContractEndpoint006View.as_view(),
        name='contract-endpoint-137',
    ),
    # API-FAV-002,API-FAV-003
    path(
        'api/v1/me/favorite-hospitals/<str:hospital_id>',
        patients_contract_views.PatientsContractEndpoint007View.as_view(),
        name='contract-endpoint-138',
    ),
    # API-RX-001,API-RX-005
    path(
        'api/v1/prescriptions',
        prescriptions_contract_views.PrescriptionsContractEndpoint001View.as_view(),
        name='contract-endpoint-139',
    ),
    # API-RX-002,API-RX-003
    path(
        'api/v1/prescriptions/<str:prescription_id>',
        prescriptions_contract_views.PrescriptionsContractEndpoint002View.as_view(),
        name='contract-endpoint-140',
    ),
    # API-RX-004
    path(
        'api/v1/prescriptions/<str:prescription_id>/finalize',
        prescriptions_contract_views.PrescriptionsContractEndpoint003View.as_view(),
        name='contract-endpoint-141',
    ),
    # API-RAD-001
    path(
        'api/v1/radiology/worklist',
        radiology_contract_views.RadiologyContractEndpoint001View.as_view(),
        name='contract-endpoint-142',
    ),
    # API-RAD-002
    path(
        'api/v1/radiology-reports',
        radiology_contract_views.RadiologyContractEndpoint002View.as_view(),
        name='contract-endpoint-143',
    ),
    # API-RAD-003,API-RAD-004
    path(
        'api/v1/radiology-reports/<str:report_id>',
        radiology_contract_views.RadiologyContractEndpoint003View.as_view(),
        name='contract-endpoint-144',
    ),
    # API-RAD-005
    path(
        'api/v1/radiology-reports/<str:report_id>/submit-preliminary',
        radiology_contract_views.RadiologyContractEndpoint004View.as_view(),
        name='contract-endpoint-145',
    ),
    # API-RAD-006
    path(
        'api/v1/radiology-reports/<str:report_id>/finalize',
        radiology_contract_views.RadiologyContractEndpoint005View.as_view(),
        name='contract-endpoint-146',
    ),
    # API-RAD-007
    path(
        'api/v1/radiology-reports/<str:report_id>/amend',
        radiology_contract_views.RadiologyContractEndpoint006View.as_view(),
        name='contract-endpoint-147',
    ),
    # API-RAD-008
    path(
        'api/v1/radiology-reports/<str:report_id>/revisions',
        radiology_contract_views.RadiologyContractEndpoint007View.as_view(),
        name='contract-endpoint-148',
    ),
    # API-RAD-009,API-RAD-010
    path(
        'api/v1/radiology-reports/<str:report_id>/measurements',
        radiology_contract_views.RadiologyContractEndpoint008View.as_view(),
        name='contract-endpoint-149',
    ),
    # API-RAD-011
    path(
        'api/v1/radiology-reports/<str:report_id>/cancel',
        radiology_contract_views.RadiologyContractEndpoint009View.as_view(),
        name='contract-endpoint-150',
    ),
]
