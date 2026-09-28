import {
  describe,
  expect,
  it,
} from "vitest";

import {
  prepareClinicalContextForPrompt,
} from "./emergency_prompt_context.js";


describe("prepareClinicalContextForPrompt", () => {
  it("limits emergency prompt data to unique patients and display fields", () => {
    const clinicalContext = {
      get_emergency_worklist: {
        event_count: 3,
        patient_count: 2,
        items: [
          {
            patient_id: "patient-1",
            patient_name: "김수아",
            patient_no: "P-001",
            occurred_at: "2026-09-28T09:00:00+09:00",
            status: "ACKNOWLEDGED",
            event_type: "EMERGENCY_DETECTED",
            priority: "EMERGENCY",
            assigned_neurologist: "담당의",
          },
          {
            patient_id: "patient-1",
            patient_name: "김수아",
            patient_no: "P-001",
            occurred_at: "2026-09-28T08:00:00+09:00",
            status: "NOTIFIED",
            priority: "URGENT",
          },
          {
            patient_id: "patient-2",
            patient_name: "이민호",
            patient_no: "P-002",
            occurred_at: "2026-09-28T07:00:00+09:00",
            status: "UNRECOGNIZED",
          },
        ],
      },
    };

    const result = prepareClinicalContextForPrompt(clinicalContext);

    expect(result.get_emergency_worklist).toEqual({
      scope: "현재 종료되지 않은 진료 건에 연결된 응급 환자",
      patient_count: 2,
      patients: [
        {
          patient_name: "김수아",
          patient_no: "P-001",
          occurred_at: "2026-09-28T09:00:00+09:00",
          status: "확인 완료",
        },
        {
          patient_name: "이민호",
          patient_no: "P-002",
          occurred_at: "2026-09-28T07:00:00+09:00",
        },
      ],
    });
    expect(clinicalContext.get_emergency_worklist.items[0].priority).toBe(
      "EMERGENCY",
    );
  });
});
