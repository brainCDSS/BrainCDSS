import {
  Client,
  StreamableHTTPClientTransport,
} from "@modelcontextprotocol/client";


const CLINICAL_TOOLS = [
  "get_patient_summary",
  "get_appointments",
  "get_current_medications",
  "get_medication_safety_result",
  "get_recent_test_results",
  "get_imaging_analysis_result",
  "get_clinical_record_summary",
] as const;


export type AssistantMcpRole =
  | "patient"
  | "clinician";


export type ClinicalContextRequest = {
  actorId: string;
  actorRole: AssistantMcpRole;
  patientId: string;
  patientScope: string[];
  traceId: string;
};


export async function
fetchClinicalContext(
  request: ClinicalContextRequest,
): Promise<Record<string, unknown>> {

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
      new URL(serverUrl),
    );

  await client.connect(transport);

  try {
    const context:
      Record<string, unknown> = {};

    for (
      const toolName
      of CLINICAL_TOOLS
    ) {
      const result =
        await client.callTool({
          name: toolName,
          arguments: {
            actor_id:
              request.actorId,
            actor_role:
              request.actorRole,
            patient_scope:
              request.patientScope,
            trace_id:
              request.traceId,
            patient_id:
              request.patientId,
          },
        });

      if (result.isError) {
        throw new Error(
          `MCP_TOOL_FAILED:${toolName}`
        );
      }

      context[toolName] =
        result.structuredContent
        ?? {
          content: result.content,
        };
    }

    return context;
  } finally {
    try {
      await transport
        .terminateSession();
    } catch {
      // 세션 종료를 지원하지 않는 경우
      // client.close()로 연결을 정리한다.
    }

    await client.close();
  }
}
