import { apiRequest } from "../../api/client";
import type { RadiologyReport, RadiologyWorklistResponse } from "./types";
export function getRadiologyWorklist(state?:string){return apiRequest<RadiologyWorklistResponse>(`/api/v1/radiology/worklist${state?`?report_state=${encodeURIComponent(state)}`:""}`)}
export function getRadiologyReport(id:string){return apiRequest<RadiologyReport>(`/api/v1/radiology-reports/${encodeURIComponent(id)}`)}
