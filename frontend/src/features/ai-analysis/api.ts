import { apiRequest } from "../../api/client";
import type { AIAnalysisDetail, AIAnalysisItem, AIAnalysisListResponse, AIAnalysisResult, AIResultReview, AIResultReviewList } from "./types";

export function getAIAnalyses(status?: string): Promise<AIAnalysisListResponse> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiRequest<AIAnalysisListResponse>(`/api/v1/ai-analyses${query}`);
}

export function getAIAnalysisResult(analysisId: string): Promise<AIAnalysisResult> {
  return apiRequest<AIAnalysisResult>(
    `/api/v1/ai-analyses/${encodeURIComponent(analysisId)}/result`,
  );
}

export function getAIAnalysis(analysisId: string) { return apiRequest<AIAnalysisDetail>(`/api/v1/ai-analyses/${encodeURIComponent(analysisId)}`); }
export function requestAIAnalysis(payload: { study_id: string; series_ids: string[]; analysis_type: string; priority: "NORMAL" | "HIGH" | "CRITICAL" }, idempotencyKey: string) {
  return apiRequest<AIAnalysisItem>("/api/v1/ai-analyses", { method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey }, body: JSON.stringify(payload) });
}
export function cancelAIAnalysis(analysisId: string, reason: string) { return apiRequest<AIAnalysisDetail>(`/api/v1/ai-analyses/${encodeURIComponent(analysisId)}/cancel`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reason }) }); }
export function getAIResultReviews(resultId: string) { return apiRequest<AIResultReviewList>(`/api/v1/ai-results/${encodeURIComponent(resultId)}/reviews`); }
export function createAIResultReview(resultId: string, payload: { decision: "ACCEPT" | "MODIFY" | "REJECT"; comment: string; corrected_findings?: Record<string, unknown> }) { return apiRequest<AIResultReview>(`/api/v1/ai-results/${encodeURIComponent(resultId)}/reviews`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); }
