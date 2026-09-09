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
         * 로그인 아이디는 소문자로 통일한다.
         * 앞뒤 공백도 제거한다.
         */
        login_id:
          request.login_id
            .trim()
            .toLowerCase(),

        /**
         * 비밀번호는 대소문자를 구분하므로
         * trim 또는 소문자 변환을 하지 않는다.
         */
        password: request.password,
      }),
    },
  );

}