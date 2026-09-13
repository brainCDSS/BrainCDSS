export type AssistantContextScope =
  | "TODAY"
  | "PATIENT"
  | "ENCOUNTER";

export interface AssistantContext {
  scope: AssistantContextScope;

  patient_id?: string | null;

  encounter_id?: string | null;
}

export interface AssistantMessageRequest {
  message: string;

  conversation_id?: string | null;

  context: AssistantContext;
}

export interface AssistantAction {
  type:
    | "OPEN_APPOINTMENTS"
    | "OPEN_PATIENT"
    | "OPEN_IMAGING"
    | "OPEN_CONSULTATIONS"
    | string;

  label: string;

  target_id?: string | null;
}

export interface AssistantMessageResponse {
  conversation_id: string;

  message_id: string;

  answer: string;

  actions?: AssistantAction[];

  created_at: string;
}

export interface AssistantChatMessage {
  id: string;

  role:
    | "user"
    | "assistant";

  content: string;

  createdAt: string;

  actions?: AssistantAction[];
}