import type { SidebarMenuKey } from "./Sidebar";
import type { RoleCode } from "../../features/auth/types";

export const MENU_LABELS: Record<SidebarMenuKey, string> = {
  dashboard: "Dashboard",
  patients: "환자 관리",
  worklist: "응급 Worklist",
  triage: "접수",
  "clinical-notes": "진료기록",
  appointments: "예약 · 일정",
  imaging: "검사 / 영상",
  "ai-results": "AI 분석 결과",
  "radiology-reports": "최종 판독",
  cdss: "CDSS 결과",
  consultations: "협진",
  prescriptions: "처방 / DUR",
  notifications: "알림 센터",
  // [추가] 관리자 메뉴
  "admin-users": "사용자 · 권한",
  "admin-ml": "ML 관리",
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

  "clinical-notes": [
    "NEUROLOGIST",
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
    "RADIOLOGY",
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
  "admin-ml": ["SYSTEM_ADMIN"],
  "admin-settings": ["SYSTEM_ADMIN"],
  // [추가 끝] 관리자 메뉴
};


/* =========================================================
   메뉴 접근 여부
========================================================= */

const MASTER_CLINICAL_ROLES: readonly RoleCode[] = [
  "NURSE",
  "NEUROLOGIST",
  "NEUROSURGEON",
  "RADIOLOGY",
];

export function canAccessMenu(
  roleCode: RoleCode,
  menuKey: SidebarMenuKey,
): boolean {
  const allowedRoles =
    MENU_ALLOWED_ROLES[menuKey];

  if (
    allowedRoles.includes(
      roleCode,
    )
  ) {
    return true;
  }

  if (
    roleCode !== "MASTER"
  ) {
    return false;
  }

  return MASTER_CLINICAL_ROLES.some(
    (clinicalRole) =>
      allowedRoles.includes(
        clinicalRole,
      ),
  );
}
