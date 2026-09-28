import {
  describe,
  expect,
  it,
} from "vitest";

import {
  selectClinicalToolsForMessage,
} from "./client.js";


describe(
  "selectClinicalToolsForMessage",
  () => {

    it(
      "일반 의학 질문은 MCP Tool을 선택하지 않는다",
      () => {
        expect(
          selectClinicalToolsForMessage(
            "뇌경색이 뭐야?",
          ),
        ).toEqual([]);
      },
    );


    it(
      "오늘 예약현황은 Global 예약 Tool만 선택한다",
      () => {
        expect(
          selectClinicalToolsForMessage(
            "오늘 예약환자 현황 알려줘",
          ),
        ).toEqual([
          "get_today_appointments",
        ]);
      },
    );


    it(
      "응급환자 현황은 Emergency Global Tool을 선택한다",
      () => {
        expect(
          selectClinicalToolsForMessage(
            "현재 응급환자 현황 알려줘",
          ),
        ).toEqual([
          "get_emergency_worklist",
        ]);
      },
    );


    it(
      "미처리 협진 질문은 Pending Consultation Tool을 선택한다",
      () => {
        expect(
          selectClinicalToolsForMessage(
            "아직 답변 안 된 협진 몇 건이야?",
          ),
        ).toEqual([
          "get_pending_consultations",
        ]);
      },
    );


    it(
      "현재 처방약 질문은 Medication Tool만 선택한다",
      () => {
        expect(
          selectClinicalToolsForMessage(
            "이 환자의 현재 처방약 알려줘",
          ),
        ).toEqual([
          "get_current_medications",
        ]);
      },
    );


    it(
      "특정 환자 예약 질문은 Patient Appointment Tool을 선택한다",
      () => {
        expect(
          selectClinicalToolsForMessage(
            "이 환자 예약 일정 알려줘",
          ),
        ).toEqual([
          "get_appointments",
        ]);
      },
    );


    it(
      "한 질문에 필요한 여러 Tool을 선택할 수 있다",
      () => {
        expect(
          selectClinicalToolsForMessage(
            "현재 처방약과 CT 결과 알려줘",
          ),
        ).toEqual([
          "get_current_medications",
          "get_imaging_analysis_result",
        ]);
      },
    );


    it(
      "일반 병용금기 개념 질문은 환자 DUR 조회를 하지 않는다",
      () => {
        expect(
          selectClinicalToolsForMessage(
            "병용금기가 뭐야?",
          ),
        ).toEqual([]);
      },
    );
    it(
      "내 예약 질문은 환자 예약 조회 도구를 선택한다",
      () => {
        expect(
          selectClinicalToolsForMessage(
            "내가 예약한게 있나?",
          ),
        ).toEqual([
          "get_appointments",
        ]);
      },
    );
  },
);
