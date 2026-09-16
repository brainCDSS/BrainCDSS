import {
  randomUUID,
} from "node:crypto";

import {
  createServer,
  type IncomingMessage,
  type ServerResponse,
} from "node:http";

import { z } from "zod";

import {
  providerMode,
  providerModel,
  runChat,
} from "../flows/chat.js";


const port =
  Number(
    process.env.PORT ?? 8200
  );


/*
 * ============================================================
 * Assistant /chat Request Schema
 * ============================================================
 *
 * 36-G 변경:
 *
 * 기존:
 * - patient_id 필수
 * - patient_scope 최소 1개 필수
 *
 * 변경:
 * - Global Tool / 일반 질문은 patient_id 없이 허용
 * - 환자 미선택 상태에서는 patient_scope = [] 허용
 *
 * Patient Tool이 실제 필요한지는 runChat()에서
 * 질문을 분석한 후 다시 검증한다.
 * ============================================================
 */

const chatRequestSchema =
  z.object({
    actor_id:
      z.string()
        .trim()
        .min(1),

    role:
      z.enum([
        "patient",
        "clinician",
      ]),

    /*
     * 특정 환자를 대상으로 하지 않는
     * Global / 일반 질문에서는 patient_id가 없을 수 있다.
     *
     * 허용 형태:
     *
     * patient_id: "UUID"
     * patient_id: null
     * patient_id 생략
     */
    patient_id:
      z.string()
        .uuid()
        .nullable()
        .optional(),

    /*
     * 기존에는 최소 1개 환자 UUID를 요구했다.
     *
     * 그러나 Global / 일반 질문에서는
     * 특정 환자 scope가 필요하지 않기 때문에
     * 빈 배열 []도 정상이다.
     *
     * Patient Tool을 사용할 경우의 실제 권한 검사는
     * runChat() + MCP Registry에서 다시 수행한다.
     */
    patient_scope:
      z.array(
        z.string().uuid()
      )
        .max(100),

    message:
      z.string()
        .trim()
        .min(1)
        .max(4000),

    trace_id:
      z.string()
        .uuid()
        .optional(),
  });


/*
 * ============================================================
 * JSON Response
 * ============================================================
 */

function sendJson(
  response: ServerResponse,
  statusCode: number,
  body: unknown,
) {
  response.writeHead(
    statusCode,
    {
      "content-type":
        "application/json; charset=utf-8",
    },
  );

  response.end(
    JSON.stringify(body)
  );
}


/*
 * ============================================================
 * HTTP Request Body Reader
 * ============================================================
 */

async function readJsonBody(
  request: IncomingMessage,
): Promise<unknown> {

  const chunks: Buffer[] = [];
  let totalBytes = 0;

  for await (
    const chunk of request
  ) {
    const buffer =
      Buffer.isBuffer(chunk)
        ? chunk
        : Buffer.from(chunk);

    totalBytes += buffer.length;

    if (totalBytes > 65536) {
      throw new Error(
        "REQUEST_BODY_TOO_LARGE"
      );
    }

    chunks.push(buffer);
  }

  if (chunks.length === 0) {
    return {};
  }

  const raw =
    Buffer
      .concat(chunks)
      .toString("utf-8");

  return JSON.parse(raw);
}


/*
 * ============================================================
 * Assistant HTTP Server
 * ============================================================
 */

export const server =
  createServer(
    async (
      request,
      response,
    ) => {

      /*
       * --------------------------------------------------------
       * Health Check
       * --------------------------------------------------------
       */

      if (
        request.method === "GET"
        && request.url === "/health"
      ) {
        sendJson(
          response,
          200,
          {
            status: "ok",

            service:
              "assistant-service",

            provider:
              providerMode,

            model:
              providerModel,

            mcp_server_url:
              process.env
                .MCP_SERVER_URL
              ?? null,
          },
        );

        return;
      }


      /*
       * --------------------------------------------------------
       * Assistant Chat
       * --------------------------------------------------------
       */

      if (
        request.method === "POST"
        && request.url === "/chat"
      ) {
        let rawBody: unknown;


        /*
         * ------------------------------------------------------
         * STEP 1
         * JSON Body 읽기
         * ------------------------------------------------------
         */

        try {
          rawBody =
            await readJsonBody(
              request
            );

        } catch {
          sendJson(
            response,
            400,
            {
              code:
                "INVALID_JSON_BODY",
            },
          );

          return;
        }


        /*
         * ------------------------------------------------------
         * STEP 2
         * Request Schema 검증
         * ------------------------------------------------------
         */

        const parsed =
          chatRequestSchema
            .safeParse(rawBody);

        if (!parsed.success) {
          sendJson(
            response,
            400,
            {
              code:
                "CHAT_INPUT_INVALID",

              issues:
                parsed.error.issues,
            },
          );

          return;
        }


        const input =
          parsed.data;


        /*
         * ------------------------------------------------------
         * STEP 3
         * 명시적으로 patient_id가 들어온 경우
         * patient_scope 1차 검증
         * ------------------------------------------------------
         *
         * 기존:
         *
         * patient_id가 항상 존재한다고 가정하고
         * 무조건 scope 검사를 수행했다.
         *
         * 변경:
         *
         * patient_id가 있는 경우에만 검사한다.
         *
         * Global / 일반 질문:
         *
         * patient_id 없음
         * patient_scope = []
         *
         * → 여기서 차단하지 않는다.
         *
         * Patient 질문:
         *
         * patient_id 있음
         *
         * → patient_scope 안에 있어야 한다.
         * ------------------------------------------------------
         */

        if (
          input.patient_id
          &&
          !input.patient_scope
            .includes(
              input.patient_id
            )
        ) {
          sendJson(
            response,
            403,
            {
              code:
                "PATIENT_SCOPE_FORBIDDEN",
            },
          );

          return;
        }


        /*
         * ------------------------------------------------------
         * STEP 4
         * Trace ID
         * ------------------------------------------------------
         */

        const traceId =
          input.trace_id
          ?? randomUUID();


        /*
         * ------------------------------------------------------
         * STEP 5
         * Chat Flow 실행
         * ------------------------------------------------------
         */

        try {
          const result =
            await runChat({
              actorId:
                input.actor_id,

              role:
                input.role,

              /*
               * patient_id는 이제
               * string | null | undefined 가능.
               *
               * Patient Tool이 필요한 질문인데
               * patient_id가 없으면 runChat()에서
               * PATIENT_CONTEXT_REQUIRED를 발생시킨다.
               */
              patientId:
                input.patient_id,

              patientScope:
                input.patient_scope,

              traceId,

              message:
                input.message,
            });


          sendJson(
            response,
            200,
            result,
          );


        } catch (error) {

          /*
           * ----------------------------------------------------
           * Patient Context Required
           * ----------------------------------------------------
           *
           * 예:
           *
           * patient_id 없음
           *
           * 질문:
           * "현재 처방약 알려줘"
           *
           * → Patient Tool 필요
           * → patient_id 필요
           * → HTTP 400
           *
           * 이것은 Assistant 장애가 아니라
           * 요청 Context가 부족한 것이다.
           * ----------------------------------------------------
           */

          if (
            error instanceof Error
            &&
            error.message
              === "PATIENT_CONTEXT_REQUIRED"
          ) {
            sendJson(
              response,
              400,
              {
                code:
                  "PATIENT_CONTEXT_REQUIRED",

                trace_id:
                  traceId,
              },
            );

            return;
          }


          /*
           * ----------------------------------------------------
           * Patient Scope Forbidden
           * ----------------------------------------------------
           *
           * patient_id는 존재하지만
           * 해당 사용자의 patient_scope에 없으면
           * 권한 오류이므로 HTTP 403.
           * ----------------------------------------------------
           */

          if (
            error instanceof Error
            &&
            error.message
              === "PATIENT_SCOPE_FORBIDDEN"
          ) {
            sendJson(
              response,
              403,
              {
                code:
                  "PATIENT_SCOPE_FORBIDDEN",

                trace_id:
                  traceId,
              },
            );

            return;
          }


          /*
           * ----------------------------------------------------
           * 실제 Assistant / MCP / Gemini 장애
           * ----------------------------------------------------
           */

          console.error(
            "CHAT_EXECUTION_FAILED",
            {
              traceId,
              error,
            },
          );

          sendJson(
            response,
            502,
            {
              code:
                "CHAT_EXECUTION_FAILED",

              trace_id:
                traceId,
            },
          );
        }

        return;
      }


      /*
       * --------------------------------------------------------
       * Unknown Route
       * --------------------------------------------------------
       */

      sendJson(
        response,
        404,
        {
          code: "NOT_FOUND",
        },
      );
    },
  );


/*
 * ============================================================
 * Server Start
 * ============================================================
 *
 * Test 환경에서는 직접 listen하지 않는다.
 * ============================================================
 */

if (
  process.env.NODE_ENV
  !== "test"
) {
  server.listen(
    port,
    "0.0.0.0",
  );
}