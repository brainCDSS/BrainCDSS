import type { SidebarMenuKey } from "./Sidebar";

export const MENU_LABELS: Record<SidebarMenuKey, string> = {
  dashboard: "Dashboard",
  patients: "환자 관리",
  worklist: "응급 Worklist",
  triage: "접수 · 초기평가",
  imaging: "검사 / 영상",
  "ai-results": "AI 분석 결과",
  "radiology-reports": "최종 판독",
  cdss: "CDSS 결과",
  consultations: "협진",
  "surgical-planning": "수술 · 시술 플래닝",
  prescriptions: "처방 / DUR",
  notifications: "알림 센터",
};
