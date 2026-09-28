import {
  fetchClinicalContext,
  isPatientClinicalTool,
  selectClinicalToolsForMessage,
} from "../mcp-client/client.js";

import {
  prepareClinicalContextForPrompt,
} from "./emergency_prompt_context.js";

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


/*
 * ============================================================
 * Assistant Chat 입력 구조
 * ============================================================
 *
 * actorId
 *   → 현재 로그인한 사용자 ID
 *
 * role
 *   → Assistant에서 사용하는 사용자 역할
 *
 * patientId
 *   → 특정 환자를 대상으로 하는 질문일 때 사용
 *
 *     Patient Tool:
 *       patientId 필요
 *
 *     Global Tool / 일반 질문:
 *       patientId 없어도 됨
 *
 * patientScope
 *   → 현재 사용자가 접근 가능한 환자 범위
 *
 * traceId
 *   → Django → Assistant → MCP → Django 요청 추적용 ID
 *
 * message
 *   → 사용자가 입력한 실제 질문
 * ============================================================
 */

export type ChatInput = {
  actorId: string;

  role: AssistantRole;

  /*
   * Dashboard / TODAY / 일반 질문에서는
   * 환자가 선택되지 않을 수 있다.
   *
   * Patient Tool이 실제 선택되면
   * runChat() 내부에서 patientId 존재 여부를 검사한다.
   */
  patientId?: string | null;

  patientScope: string[];

  traceId: string;

  message: string;
};


/*
 * ============================================================
 * Assistant Chat 실행
 * ============================================================
 */

export async function runChat(
  input: ChatInput,
) {

  /*
   * ==========================================================
   * STEP 1
   * 사용자 질문에 필요한 MCP Tool 선택
   * ==========================================================
   *
   * 예:
   *
   * "현재 처방약 알려줘"
   * → get_current_medications
   *
   * "오늘 예약환자 현황 알려줘"
   * → get_today_appointments
   *
   * "현재 응급환자 현황 알려줘"
   * → get_emergency_worklist
   *
   * "아직 답변 안 된 협진 알려줘"
   * → get_pending_consultations
   *
   * "뇌경색이 뭐야?"
   * → []
   *
   * 일반 질문은 MCP Tool을 선택하지 않는다.
   * ==========================================================
   */

  const selectedTools =
    selectClinicalToolsForMessage(
      input.message,
    );


  /*
   * ==========================================================
   * STEP 2
   * 선택된 Tool 중 Patient Tool이 있는지 확인
   * ==========================================================
   *
   * Patient Tool:
   *
   * get_patient_summary
   * get_appointments
   * get_current_medications
   * get_medication_safety_result
   * get_recent_test_results
   * get_imaging_analysis_result
   * get_clinical_record_summary
   *
   * Global Tool:
   *
   * get_today_appointments
   * get_emergency_worklist
   * get_pending_consultations
   *
   * Global Tool이나 일반 질문은
   * 특정 patientId가 없어도 된다.
   * ==========================================================
   */

  const requiresPatientContext =
    selectedTools.some(
      isPatientClinicalTool,
    );


  /*
   * ==========================================================
   * STEP 2-A
   * Patient Tool인데 환자가 선택되지 않은 경우 차단
   * ==========================================================
   *
   * 예:
   *
   * patientId 없음
   *
   * 질문:
   * "현재 처방약 알려줘"
   *
   * → get_current_medications 필요
   * → patientId 필요
   * → PATIENT_CONTEXT_REQUIRED
   *
   * 반대로:
   *
   * "오늘 예약환자 현황 알려줘"
   *
   * → Global Tool
   * → patientId 없어도 정상
   * ==========================================================
   */

  if (
    requiresPatientContext
    && !input.patientId
  ) {
    throw new Error(
      "PATIENT_CONTEXT_REQUIRED",
    );
  }


  /*
   * ==========================================================
   * STEP 2-B
   * Patient Tool의 patient_scope 검사
   * ==========================================================
   *
   * Patient Tool을 사용하는 경우에는
   * 기존 보안 정책을 그대로 유지한다.
   *
   * 선택된 patientId가
   * patientScope 안에 존재하지 않으면 차단한다.
   *
   * 즉 36-G에서 환자 미선택 질문을 허용한다고 해서
   * Patient Tool 보안을 완화하는 것은 아니다.
   *
   * Assistant Service에서 1차 검사하고,
   * MCP Registry에서도 다시 검사한다.
   * ==========================================================
   */

  if (
    requiresPatientContext
    && input.patientId
    && !input.patientScope.includes(
      input.patientId,
    )
  ) {
    throw new Error(
      "PATIENT_SCOPE_FORBIDDEN",
    );
  }


  /*
   * ==========================================================
   * STEP 3
   * 선택된 MCP Tool만 실행
   * ==========================================================
   *
   * 기존:
   *
   * 질문과 상관없이 7개 Patient Tool 전부 호출
   *
   * 변경:
   *
   * 질문에 필요한 Tool만 호출
   *
   * selectedTools = []
   * 인 일반 질문은
   * fetchClinicalContext() 내부에서
   * MCP Server에 연결하지 않고 바로 {}를 반환한다.
   * ==========================================================
   */

  const clinicalContext =
    await fetchClinicalContext({
      actorId:
        input.actorId,

      actorRole:
        input.role,

      patientId:
        input.patientId,

      patientScope:
        input.patientScope,

      traceId:
        input.traceId,

      toolNames:
        selectedTools,
    });

  const promptClinicalContext =
    prepareClinicalContextForPrompt(
      clinicalContext,
    );


  /*
   * ==========================================================
   * STEP 4
   * Gemini에 전달할 Context 설명 구성
   * ==========================================================
   *
   * MCP Tool을 실제 사용한 질문과
   * 일반 지식 질문을 구분한다.
   * ==========================================================
   */

  const contextSection =
    selectedTools.length > 0

      ? `
다음은 BrainOn MCP를 통해 Django에서 조회한
질문 관련 Read-only Clinical Context이다.

<clinical_context>
${JSON.stringify(
  promptClinicalContext,
  null,
  2,
)}
</clinical_context>

위 Clinical Context에 포함된 임상/업무 사실만 근거로 사용한다.
Clinical Context에 없는 환자별 사실을 추측하거나 만들어내지 않는다.
`.trim()

      : `
이 질문은 특정 환자 데이터 또는 업무 현황 조회가
필요하지 않은 일반 질문으로 분류되었다.

MCP Clinical Tool은 호출하지 않았다.

일반적인 의학/서비스 정보 범위에서 답하되
특정 환자의 상태, 검사, 진단, 처방 또는 기록을
추측해서 만들어내지 않는다.
`.trim();


  /*
   * ==========================================================
   * STEP 5
   * Gemini 최종 Prompt 생성
   * ==========================================================
   */

  const prompt = `
사용자 역할:
${input.role}

사용자 질문:
${input.message}

${contextSection}
`.trim();


  /*
   * ==========================================================
   * STEP 6
   * Gemini 호출
   * ==========================================================
   */

  const generated =
    await providerBundle
      .provider
      .generate({
        role:
          input.role,

        prompt,
      });


  /*
   * ==========================================================
   * STEP 7
   * Assistant Service 응답
   * ==========================================================
   *
   * patient_id
   *
   * Patient 질문:
   * → 실제 patientId
   *
   * Global / 일반 질문:
   * → null
   *
   * context_sources
   *
   * 실제 호출된 MCP Tool 이름만 반환한다.
   *
   * 일반 질문:
   * → []
   * ==========================================================
   */

  return {
    trace_id:
      input.traceId,

    provider:
      providerBundle.mode,

    model:
      providerBundle.model,

    patient_id:
      input.patientId ?? null,

    answer:
      generated.text,

    usage_tokens:
      generated.usageTokens,

    context_sources:
      Object.keys(
        clinicalContext,
      ),
  };
}
