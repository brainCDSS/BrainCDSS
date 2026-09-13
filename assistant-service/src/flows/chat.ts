import {
  fetchClinicalContext,
} from "../mcp-client/client.js";

import {
  createProvider,
} from "../providers/factory.js";

import type {
  AssistantRole,
} from "../providers/provider.js";


const providerBundle =
  createProvider();


export const providerMode =
  providerBundle.mode;

export const providerModel =
  providerBundle.model;


export type ChatInput = {
  actorId: string;
  role: AssistantRole;
  patientId: string;
  patientScope: string[];
  traceId: string;
  message: string;
};


export async function runChat(
  input: ChatInput,
) {
  if (
    !input.patientScope.includes(
      input.patientId
    )
  ) {
    throw new Error(
      "PATIENT_SCOPE_FORBIDDEN"
    );
  }

  const clinicalContext =
    await fetchClinicalContext({
      actorId: input.actorId,
      actorRole: input.role,
      patientId: input.patientId,
      patientScope:
        input.patientScope,
      traceId: input.traceId,
    });

  const prompt = `
사용자 역할:
${input.role}

사용자 질문:
${input.message}

다음은 BrainOn MCP를 통해 Django에서 조회한
Read-only Clinical Context이다.

<clinical_context>
${JSON.stringify(
  clinicalContext,
  null,
  2,
)}
</clinical_context>

위 Clinical Context에 근거하여 질문에 답한다.
환자별 사실을 추측하거나 새로 만들지 않는다.
`.trim();

  const generated =
    await providerBundle
      .provider
      .generate({
        role: input.role,
        prompt,
      });

  return {
    trace_id: input.traceId,
    provider: providerBundle.mode,
    model: providerBundle.model,
    patient_id: input.patientId,
    answer: generated.text,
    usage_tokens:
      generated.usageTokens,
    context_sources:
      Object.keys(
        clinicalContext
      ),
  };
}
