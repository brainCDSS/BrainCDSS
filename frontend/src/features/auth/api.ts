import {
  apiRequest,
} from "../../api/client";

import type {
  LoginRequest,
  LoginResponse,
} from "./types";


/* =========================================================
   로그인 API
   ---------------------------------------------------------
   POST /api/v1/auth/login
   ========================================================= */

export async function login(
  request: LoginRequest,
): Promise<LoginResponse> {

  return apiRequest<LoginResponse>(
    "/api/v1/auth/login",
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },

      body: JSON.stringify({
        /**
         * 로그인 아이디의 앞뒤 공백만 제거한다.
         * 대소문자 정규화는 로그인 화면에서 처리한다.
         */
        login_id:
          request.login_id
            .trim(),

        /**
         * 비밀번호는 대소문자를 구분하므로
         * trim 또는 소문자 변환을 하지 않는다.
         */
        password: request.password,
      }),
    },
  );

}

export async function logout(refresh: string): Promise<void> {
  await apiRequest<void>("/api/v1/auth/logout", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({refresh}),
  });
}
