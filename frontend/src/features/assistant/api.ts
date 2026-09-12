import { apiRequest } from "../../api/client";

import type {
  AssistantMessageRequest,
  AssistantMessageResponse,
} from "./types";

export function sendAssistantMessage(
  payload: AssistantMessageRequest,
): Promise<AssistantMessageResponse> {
  return apiRequest<AssistantMessageResponse>(
    "/api/v1/assistant/messages",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    },
  );
}