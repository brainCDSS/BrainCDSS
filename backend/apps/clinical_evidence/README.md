# Clinical Evidence

This Django app is independent from `assistant-service` and `mcp-server`. It calls
PubMed E-utilities and uses Vertex AI directly through Application Default Credentials
to pre-generate abstract-only summaries. It never reads or transmits patient data.

```powershell
python backend/manage.py migrate --settings=config.settings.local
python backend/manage.py update_clinical_evidence --dry-run
python backend/manage.py update_clinical_evidence --no-summaries
python backend/manage.py update_clinical_evidence
python backend/manage.py update_clinical_evidence --disease ischemic_stroke
```

`--dry-run` calls PubMed but performs no DB writes and no Vertex calls. READY summaries
are reused until the abstract/title/type input hash, model, or
`CLINICAL_EVIDENCE_SUMMARY_VERSION` changes.

Ranking is a display heuristic, not GRADE: Guideline/Practice Guideline,
Meta-Analysis, Systematic Review, RCT, other clinical study, then Review; date breaks
ties. Case reports, editorials, comments, letters, retractions and AI-first titles are
excluded.
