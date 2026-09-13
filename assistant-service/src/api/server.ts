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

    patient_id:
      z.string()
        .uuid(),

    patient_scope:
      z.array(
        z.string().uuid()
      )
        .min(1)
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


export const server =
  createServer(
    async (
      request,
      response,
    ) => {
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

      if (
        request.method === "POST"
        && request.url === "/chat"
      ) {
        let rawBody: unknown;

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

        if (
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

        const traceId =
          input.trace_id
          ?? randomUUID();

        try {
          const result =
            await runChat({
              actorId:
                input.actor_id,
              role:
                input.role,
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

      sendJson(
        response,
        404,
        {
          code: "NOT_FOUND",
        },
      );
    },
  );


if (
  process.env.NODE_ENV
  !== "test"
) {
  server.listen(
    port,
    "0.0.0.0",
  );
}
