import {
  Client,
  StreamableHTTPClientTransport,
} from "@modelcontextprotocol/client";


/*
 * ============================================================
 * Patient Tool
 * ============================================================
 *
 * 특정 환자 한 명을 조회하기 위해 patient_id가 필요한 Tool이다.
 *
 * 실제 patient_id / patient_scope 검증은 MCP Server의
 * Registry에서도 다시 수행한다.
 *
 * Assistant Service에서는 어떤 Tool을 호출할 것인지 선택하고,
 * Patient Tool일 경우에만 patient_id를 MCP arguments에 포함한다.
 * ============================================================
 */

export const PATIENT_CLINICAL_TOOLS = [
  "get_patient_summary",
  "get_appointments",
  "get_current_medications",
  "get_medication_safety_result",
  "get_recent_test_results",
  "get_imaging_analysis_result",
  "get_clinical_record_summary",
] as const;


/*
 * ============================================================
 * Global Tool
 * ============================================================
 *
 * 특정 환자 한 명이 아니라 전체 업무 현황을 조회하는 Tool이다.
 *
 * Global Tool에는 patient_id를 전달하지 않는다.
 *
 * 현재 구현:
 *
 * - 오늘 예약 현황
 * - 현재 응급환자 Worklist
 * - 처리 대기 중 협진 Worklist
 * ============================================================
 */

export const GLOBAL_CLINICAL_TOOLS = [
  "get_today_appointments",
  "get_emergency_worklist",
  "get_pending_consultations",
] as const;


export type PatientClinicalToolName =
  typeof PATIENT_CLINICAL_TOOLS[number];


export type GlobalClinicalToolName =
  typeof GLOBAL_CLINICAL_TOOLS[number];


export type ClinicalToolName =
  | PatientClinicalToolName
  | GlobalClinicalToolName;


/*
 * Patient Tool 여부를 빠르게 검사하기 위한 Set.
 *
 * Patient Tool이면 MCP 호출 시 patient_id를 추가하고,
 * Global Tool이면 patient_id를 추가하지 않는다.
 */

const PATIENT_TOOL_SET =
  new Set<string>(
    PATIENT_CLINICAL_TOOLS,
  );


export function isPatientClinicalTool(
  toolName: ClinicalToolName,
): toolName is PatientClinicalToolName {
  return PATIENT_TOOL_SET.has(
    toolName,
  );
}


/*
 * ============================================================
 * 질문 정규화
 * ============================================================
 *
 * 사용자가:
 *
 * "오늘 예약 현황"
 * "오늘예약현황"
 *
 * 처럼 띄어쓰기를 다르게 입력해도 같은 질문으로 판단하기 위해
 * 공백을 제거하고 영문은 소문자로 통일한다.
 * ============================================================
 */

function compactMessage(
  message: string,
): string {
  return message
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "");
}


function includesAny(
  message: string,
  patterns: readonly string[],
): boolean {
  return patterns.some(
    (pattern) =>
      message.includes(
        pattern
          .toLowerCase()
          .replace(/\s+/g, ""),
      ),
  );
}


/*
 * ============================================================
 * 질문 → MCP Tool 선택
 * ============================================================
 *
 * 지금 단계에서는 LLM에게 Tool 선택 권한을 직접 주지 않는다.
 *
 * 이유:
 *
 * 1. 현재 Provider Interface가 단순 generate() 구조이다.
 * 2. 기존 Provider 구조를 크게 변경하지 않는다.
 * 3. Clinical MCP는 허용된 Read-only Tool만 명시적으로 사용한다.
 * 4. 질문과 무관한 임상데이터 조회를 줄인다.
 *
 * 하나의 질문에서 여러 종류의 데이터가 필요하면
 * 여러 Tool을 선택할 수도 있다.
 *
 * 예:
 *
 * "현재 처방약과 영상 분석 결과 알려줘"
 *
 * →
 *
 * get_current_medications
 * get_imaging_analysis_result
 * ============================================================
 */

export function selectClinicalToolsForMessage(
  message: string,
): ClinicalToolName[] {

  const normalized =
    compactMessage(
      message,
    );

  const selected =
    new Set<ClinicalToolName>();


  /*
   * ----------------------------------------------------------
   * Global Tool 1
   * 오늘 전체 예약 현황
   * ----------------------------------------------------------
   */

  if (
    includesAny(
      normalized,
      [
        "오늘예약",
        "금일예약",
        "오늘예약환자",
        "예약환자현황",
        "오늘예약현황",
      ],
    )
  ) {
    selected.add(
      "get_today_appointments",
    );
  }


  /*
   * ----------------------------------------------------------
   * Global Tool 2
   * 현재 응급환자 현황
   * ----------------------------------------------------------
   */

  if (
    includesAny(
      normalized,
      [
        "현재응급환자",
        "응급환자현황",
        "응급현황",
        "응급워크리스트",
        "응급worklist",
      ],
    )
  ) {
    selected.add(
      "get_emergency_worklist",
    );
  }


  /*
   * ----------------------------------------------------------
   * Global Tool 3
   * 처리 대기 중 협진
   * ----------------------------------------------------------
   */

  if (
    includesAny(
      normalized,
      [
        "대기중협진",
        "대기중인협진",
        "협진대기",
        "미처리협진",
        "처리대기협진",
        "처리안된협진",
        "답변안된협진",
        "회신안된협진",
        "협진현황",
      ],
    )
  ) {
    selected.add(
      "get_pending_consultations",
    );
  }


  /*
   * ----------------------------------------------------------
   * Patient Tool 1
   * 환자 기본 요약
   * ----------------------------------------------------------
   */

  if (
    includesAny(
      normalized,
      [
        "이환자요약",
        "환자요약",
        "이환자정보",
        "환자기본정보",
        "환자정보요약",
      ],
    )
  ) {
    selected.add(
      "get_patient_summary",
    );
  }


  /*
   * ----------------------------------------------------------
   * Patient Tool 2
   * 특정 환자의 예약
   *
   * 오늘 전체 예약이 이미 선택된 경우에는
   * get_appointments를 중복 호출하지 않는다.
   * ----------------------------------------------------------
   */

  if (
    !selected.has(
      "get_today_appointments",
    )
    &&
    includesAny(
      normalized,
      [
        "이환자예약",
        "환자예약이력",
        "예약이력",
        "예약일정",
        "다음예약",
      ],
    )
  ) {
    selected.add(
      "get_appointments",
    );
  }


  // 환자앱에서 "내가 예약한 게 있나?"처럼 묻는 표현도
  // 로그인 환자 범위의 예약 조회로 처리한다.
  if (
    !selected.has(
      "get_today_appointments",
    )
    &&
    includesAny(
      normalized,
      [
        "내가 예약",
        "내 예약",
        "예약한 게 있나",
        "예약했나",
      ],
    )
  ) {
    selected.add(
      "get_appointments",
    );
  }


  /*
   * ----------------------------------------------------------
   * Patient Tool 3
   * 현재 약물
   * ----------------------------------------------------------
   */

  if (
    includesAny(
      normalized,
      [
        "현재약물",
        "현재약",
        "처방약",
        "복용약",
        "복용중인약",
        "투약중인약",
        "투약중인약물",
      ],
    )
  ) {
    selected.add(
      "get_current_medications",
    );
  }


  /*
   * ----------------------------------------------------------
   * Patient Tool 4
   * Medication Safety / DUR
   *
   * "병용금기가 뭐야?" 같은 일반 개념 질문은
   * MCP를 호출하지 않도록 "있", "결과" 등의
   * 환자/처방 조회 표현을 중심으로 잡는다.
   * ----------------------------------------------------------
   */

  if (
    includesAny(
      normalized,
      [
        "dur결과",
        "약물안전결과",
        "처방안전성",
        "안전성검사결과",
        "병용금기있",
        "상호작용있",
        "용량주의있",
      ],
    )
  ) {
    selected.add(
      "get_medication_safety_result",
    );
  }


  /*
   * ----------------------------------------------------------
   * Patient Tool 5
   * 최근 검사 결과
   * ----------------------------------------------------------
   */

  if (
    includesAny(
      normalized,
      [
        "최근검사결과",
        "검사결과",
        "최근검사",
      ],
    )
  ) {
    selected.add(
      "get_recent_test_results",
    );
  }


  /*
   * ----------------------------------------------------------
   * Patient Tool 6
   * 영상 / AI 분석 결과
   *
   * 단순 "MRI가 뭐야?" 같은 일반 질문에서는
   * 호출되지 않도록 "결과", "분석" 표현을 사용한다.
   * ----------------------------------------------------------
   */

  if (
    includesAny(
      normalized,
      [
        "ai분석결과",
        "영상분석결과",
        "영상ai분석",
        "최근영상결과",
        "ct결과",
        "mri결과",
        "mra결과",
      ],
    )
  ) {
    selected.add(
      "get_imaging_analysis_result",
    );
  }


  /*
   * ----------------------------------------------------------
   * Patient Tool 7
   * 임상 / 진료 기록 요약
   * ----------------------------------------------------------
   */

  if (
    includesAny(
      normalized,
      [
        "임상기록요약",
        "진료기록요약",
        "진료기록",
        "진료요약",
        "soap기록",
        "초진기록",
      ],
    )
  ) {
    selected.add(
      "get_clinical_record_summary",
    );
  }


  return Array.from(
    selected,
  );
}


export type AssistantMcpRole =
  | "patient"
  | "clinician";


export type ClinicalContextRequest = {
  actorId: string;
  actorRole: AssistantMcpRole;

  /*
   * 36-F에서는 기존 계약을 깨지 않기 위해
   * patientId를 아직 필수로 유지한다.
   *
   * 환자 미선택 요청을 허용하는 변경은
   * 다음 단계 36-G에서 진행한다.
   */

/*
 * Global Tool 또는 일반 질문에서는
 * 특정 환자가 선택되지 않을 수 있다.
 *
 * Patient Tool이 선택된 경우에는 아래
 * fetchClinicalContext()에서 다시 필수 여부를 검사한다.
 */
  patientId?: string | null;

  patientScope: string[];
  traceId: string;

  /*
   * 기존에는 모든 Tool을 무조건 호출했다.
   *
   * 이제 질문 분석 결과로 선택된 Tool 이름만 전달한다.
   */

  toolNames: ClinicalToolName[];
};


/*
 * ============================================================
 * 선택된 MCP Tool만 호출
 * ============================================================
 *
 * 기존:
 *
 * for (CLINICAL_TOOLS 전체)
 *
 * 변경:
 *
 * for (request.toolNames)
 *
 * 즉 질문과 관련된 Tool만 실행한다.
 * ============================================================
 */

export async function
fetchClinicalContext(
  request: ClinicalContextRequest,
): Promise<Record<string, unknown>> {

  /*
   * Tool이 하나도 필요하지 않은 일반 질문이면
   * MCP Server에 연결조차 하지 않는다.
   */

  if (
    request.toolNames.length
    === 0
  ) {
    return {};
  }

/*
 * ============================================================
 * Patient Tool의 patient_id 필수 검증
 * ============================================================
 *
 * 일반 질문:
 *   toolNames = []
 *   → 위에서 이미 {} 반환
 *
 * Global Tool:
 *   patient_id 없어도 정상
 *
 * Patient Tool:
 *   patient_id 반드시 필요
 *
 * MCP Server까지 잘못된 요청을 보내기 전에
 * Assistant Service에서 1차로 차단한다.
 * ============================================================
 */

  const requiresPatientContext =
    request.toolNames.some(
      isPatientClinicalTool,
    );

  if (
    requiresPatientContext
    && !request.patientId
  ) {
    throw new Error(
      "PATIENT_CONTEXT_REQUIRED",
    );
  }

  const serverUrl =
    process.env.MCP_SERVER_URL
      ?.trim()
    || "http://localhost:8300/mcp";


  const client = new Client(
    {
      name:
        "brainon-assistant-service",
      version: "0.1.0",
    },
    {
      versionNegotiation: {
        mode: "auto",
      },
    },
  );


  const transport =
    new StreamableHTTPClientTransport(
      new URL(
        serverUrl,
      ),
    );


  await client.connect(
    transport,
  );


  try {
    const context:
      Record<string, unknown> = {};


    for (
      const toolName
      of request.toolNames
    ) {

      /*
       * 모든 MCP Tool에 공통으로 전달하는 Context.
       */

      const toolArguments:
        Record<string, unknown> = {
          actor_id:
            request.actorId,

          actor_role:
            request.actorRole,

          patient_scope:
            request.patientScope,

          trace_id:
            request.traceId,
        };


      /*
       * Patient Tool일 때만 patient_id를 전달한다.
       *
       * Global Tool:
       *
       * get_today_appointments
       * get_emergency_worklist
       * get_pending_consultations
       *
       * 에는 patient_id를 전달하지 않는다.
       */

      if (
        isPatientClinicalTool(
          toolName,
        )
      ) {
        toolArguments.patient_id =
          request.patientId;
      }


      const result =
        await client.callTool({
          name: toolName,
          arguments:
            toolArguments,
        });


      if (result.isError) {
        throw new Error(
          `MCP_TOOL_FAILED:${toolName}`,
        );
      }


      context[toolName] =
        result.structuredContent
        ?? {
          content:
            result.content,
        };
    }


    return context;

  } finally {

    try {
      await transport
        .terminateSession();

    } catch {
      /*
       * MCP Transport가 명시적인 세션 종료를
       * 지원하지 않는 경우 client.close()로 정리한다.
       */
    }


    await client.close();
  }
}
