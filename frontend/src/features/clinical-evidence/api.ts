import { apiRequest } from "../../api/client";
import type { ClinicalEvidenceResponse } from "./types";
export const getClinicalEvidence = () => apiRequest<ClinicalEvidenceResponse>("/api/v1/clinical-evidence?limit=3");
