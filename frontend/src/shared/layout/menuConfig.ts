import type { SidebarMenuKey } from "./Sidebar";
import type { RoleCode } from "../../features/auth/types";

export const MENU_LABELS: Record<SidebarMenuKey, string> = {
  dashboard: "Dashboard",
  patients: "환자 관리",
  worklist: "응급 Worklist",
  triage: "접수",
  appointments: "예약 · 일정",
  imaging: "검사 / 영상",
  "ai-results": "AI 분석 결과",
  "radiology-reports": "최종 판독",
  cdss: "CDSS 결과",
  consultations: "협진",
  "surgical-planning": "수술 · 시술 플래닝",
  prescriptions: "처방 / DUR",
  notifications: "알림 센터",
  // [추가] 관리자 메뉴
  "admin-users": "사용자 · 권한",
  "admin-monitoring": "시스템 모니터링",
  "admin-audit": "감사 로그",
  "admin-settings": "설정",
  // [추가 끝] 관리자 메뉴
};


/* =========================================================
   의료진 Role
========================================================= */

/* =========================================================
   Role별 접근 가능 메뉴
========================================================= */

export const MENU_ALLOWED_ROLES: Record<
  SidebarMenuKey,
  readonly RoleCode[]
> = {
  dashboard: [
    "NURSE",
    "NEUROLOGIST",
    "NEUROSURGEON",
    "RADIOLOGY",
    // [추가] 관리자 메뉴
    "SYSTEM_ADMIN",
    // [추가 끝] 관리자 메뉴
  ],

  patients: [
    "NURSE",
    "NEUROLOGIST",
    "NEUROSURGEON",
    "RADIOLOGY",
  ],

  /*
   * 응급환자 Worklist
   * 신경과 중심
   */
  worklist: [
    "NEUROLOGIST",
  ],

  /*
   * 접수 / 초기평가
   * 간호사
   */
  triage: [
    "NURSE",
  ],

  /*
   * 예약 · 일정
   */
  appointments: [
    "NURSE",
    "NEUROLOGIST",
    "NEUROSURGEON",
  ],

  /*
   * 영상 검사 조회
   */
  imaging: [
    "NEUROLOGIST",
    "NEUROSURGEON",
    "RADIOLOGY",
  ],

  /*
   * AI 영상분석 결과
   */
  "ai-results": [
    "NEUROLOGIST",
    "NEUROSURGEON",
    "RADIOLOGY",
  ],

  /*
   * 최종 판독
   *
   * 현재 프로젝트에서
   * 신경과 의사가 최종 판독하는 구조라면
   * 추후 NEUROLOGIST만 남겨도 됨.
   */
  "radiology-reports": [
    "NEUROLOGIST",
  ],

  /*
   * CDSS 결과
   */
  cdss: [
    "NEUROLOGIST",
    "NEUROSURGEON",
  ],

  /*
   * 협진
   */
  consultations: [
    "NEUROLOGIST",
    "NEUROSURGEON",
    "RADIOLOGY",
  ],

  /*
   * 수술 · 시술 플래닝
   */
  "surgical-planning": [
    "NEUROLOGIST",
    "NEUROSURGEON",
    "RADIOLOGY",
  ],

  /*
   * 처방 / DUR
   */
  prescriptions: [
    "NEUROLOGIST",
    "NEUROSURGEON",
  ],

  /*
   * 알림
   */
  notifications: [
    "NURSE",
    "NEUROLOGIST",
    "NEUROSURGEON",
    "RADIOLOGY",
  ],
  // [추가] 관리자 메뉴
  "admin-users": ["SYSTEM_ADMIN"],
  "admin-monitoring": ["SYSTEM_ADMIN"],
  "admin-audit": ["SYSTEM_ADMIN"],
  "admin-settings": ["SYSTEM_ADMIN"],
  // [추가 끝] 관리자 메뉴
};


/* =========================================================
   메뉴 접근 여부
========================================================= */

export function canAccessMenu(
  roleCode: RoleCode,
  menuKey: SidebarMenuKey,
): boolean {
  return MENU_ALLOWED_ROLES[menuKey].includes(
    roleCode,
  );
}
