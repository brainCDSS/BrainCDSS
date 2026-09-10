import type { AnalysisStatusItem, ServiceStatusItem } from "./types";

const unavailable = (service: string): ServiceStatusItem => ({
  service,
  status: "API 미연결",
  checkedAt: "-",
  message: "상태 조회 API가 연결되지 않았습니다.",
});

export const CORE_SERVICE_STATUS = [
  "Backend", "PostgreSQL", "Redis", "RabbitMQ", "AI Inference",
].map(unavailable);

export const INTEGRATION_SERVICE_STATUS = [
  "Orthanc", "PACS", "FHIR/HL7",
].map(unavailable);

export const AI_ANALYSIS_STATUS: AnalysisStatusItem[] = [
  "허혈성 뇌졸중", "출혈성 뇌졸중", "뇌동맥류",
].map((type) => ({ type, completed: null, running: null, failed: null }));

export const SYSTEM_ALERTS: ReadonlyArray<never> = [];
