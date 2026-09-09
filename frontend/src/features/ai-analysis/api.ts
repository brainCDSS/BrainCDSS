import { apiRequest } from "../../api/client";
import type { AIAnalysisListResponse, AIAnalysisResult } from "./types";

export function getAIAnalyses(status?: string): Promise<AIAnalysisListResponse> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiRequest<AIAnalysisListResponse>(`/api/v1/ai-analyses${query}`);
}

export function getAIAnalysisResult(analysisId: string): Promise<AIAnalysisResult> {
  return apiRequest<AIAnalysisResult>(
    `/api/v1/ai-analyses/${encodeURIComponent(analysisId)}/result`,
  );
}
