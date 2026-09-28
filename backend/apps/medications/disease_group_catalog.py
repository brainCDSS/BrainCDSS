"""Curated BrainOn medication-to-disease-group mappings."""

DISEASE_GROUP_MEDICATION_CODES = {
    "HEMORRHAGIC_STROKE": (
        "BRN-MED-NIC-001", "BRN-MED-NIC-002",
        "BRN-MED-LAB-001", "BRN-MED-LAB-002",
        "BRN-MED-MAN-001", "BRN-MED-MAN-002",
        "BRN-MED-LEV-001", "BRN-MED-LEV-002",
        "BRN-MED-FUR-001", "BRN-MED-FUR-002",
    ),
    "ISCHEMIC_STROKE": (
        "BRN-MED-ASP-001", "BRN-MED-ASP-002",
        "BRN-MED-ALT-001", "BRN-MED-ALT-002",
        "BRN-MED-ATO-001", "BRN-MED-ATO-002",
        "BRN-MED-CIL-001", "BRN-MED-CIL-002",
        "BRN-MED-API-001", "BRN-MED-API-002",
    ),
    "CEREBRAL_ANEURYSM": (
        "BRN-MED-NIM-001", "BRN-MED-NIM-002",
        "BRN-MED-ACE-001", "BRN-MED-ACE-002",
        "BRN-MED-PRO-001", "BRN-MED-PRO-002",
        "BRN-MED-OND-001", "BRN-MED-OND-002",
        "BRN-MED-NOR-001", "BRN-MED-NOR-002",
    ),
}

MAPPING_EVIDENCE_SOURCE = "BrainOn curated disease medication mapping 2026-09-28"
