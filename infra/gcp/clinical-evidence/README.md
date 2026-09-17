# Clinical Evidence daily refresh

Use the existing Backend image as a Cloud Run Job. This adds no public Scheduler
endpoint, queue, Redis, or second application image. Supply `PROJECT_ID`, `REGION`,
`BACKEND_IMAGE`, `RUNTIME_SERVICE_ACCOUNT`, `SCHEDULER_SERVICE_ACCOUNT`,
`CLOUD_SQL_INSTANCE`, and approved secret/environment configuration.

```powershell
gcloud run jobs create brainon-clinical-evidence `
  --project PROJECT_ID --region REGION --image BACKEND_IMAGE `
  --service-account RUNTIME_SERVICE_ACCOUNT `
  --command python --args manage.py,update_clinical_evidence `
  --set-cloudsql-instances CLOUD_SQL_INSTANCE --task-timeout 60m --max-retries 1 `
  --set-env-vars GOOGLE_CLOUD_PROJECT=PROJECT_ID,GOOGLE_CLOUD_LOCATION=global,CLINICAL_EVIDENCE_GEMINI_MODEL=APPROVED_MODEL,CLINICAL_EVIDENCE_SUMMARY_VERSION=abstract-v1,CLINICAL_EVIDENCE_PUBMED_EMAIL=OPS_EMAIL
```

Grant the runtime account Cloud SQL Client and Vertex AI User, plus access to only the
backend secrets. Attach an optional NCBI API key through Secret Manager, never source.
Grant the Scheduler account Cloud Run Invoker on this job.

```powershell
gcloud scheduler jobs create http brainon-clinical-evidence-daily `
  --project PROJECT_ID --location REGION --schedule "0 6 * * *" `
  --time-zone "Asia/Seoul" --http-method POST `
  --uri "https://run.googleapis.com/v2/projects/PROJECT_ID/locations/REGION/jobs/brainon-clinical-evidence:run" `
  --oauth-service-account-email SCHEDULER_SERVICE_ACCOUNT `
  --oauth-token-scope "https://www.googleapis.com/auth/cloud-platform"
```

Run migrations and execute the job once before enabling the schedule. A failed disease
refresh retains its prior active rows and `last_success_at`.
