/* =========================================================
   로그인 요청
   ========================================================= */

export interface LoginRequest {
  login_id: string;
  password: string;
}


/* =========================================================
   사용자 역할
   ========================================================= */

export type RoleCode =
  | "PATIENT"
  | "NURSE"
  | "NEUROLOGIST"
  | "NEUROSURGEON"
  | "RADIOLOGY"
  | "MASTER"
  | "SYSTEM_ADMIN";


export interface UserRole {
  code: RoleCode;
  name: string;
}


/* =========================================================
   소속 병원
   현재 Mock 응답에서만 사용하는 선택 필드
   ========================================================= */

export interface UserHospital {
  id: string;
  name: string;
}


/* =========================================================
   로그인 사용자
   ========================================================= */

export interface LoginUser {
  id: string;
  login_id: string;
  name: string;
  email: string | null;
  role: UserRole;
  permissions: string[];

  /**
   * 현재 로그인 API 공식 명세에는 없고
   * Postman Mock 화면 확인용으로만 사용한다.
   */
  hospital?: UserHospital;
}


/* =========================================================
   로그인 성공 응답
   ========================================================= */

export interface LoginResponse {
  access: string;
  refresh: string;
  user: LoginUser;
}