import type { CollaborationMessage, CollaborationUser, PlanningCase, Vector3, VirtualClip } from "./types";

// MOCK: 수술 플래닝 API가 제공되기 전까지 화면 구조와 상호작용 확인에만 사용합니다.
export const EMPTY_PLANNING_CASE: PlanningCase = {
  patient: { name: "환자 선택 필요", patientNo: "Backend 제공 없음", sex: "Backend 제공 없음", age: "Backend 제공 없음" },
  examination: { diagnosis: "임상 진단 연동 필요", studyName: "영상 검사 연동 필요", studyDate: "연동 필요" },
  assignment: { department: "Backend 제공 없음", clinician: "Backend 제공 없음", status: "미연결" },
  aiSummary: { finding: "AI 분석 결과 연동 필요", confidence: "연동 필요", lesionLocation: "연동 필요" },
};
export const MOCK_VIRTUAL_CLIPS: VirtualClip[] = [
  { id: "mock-standard-06", name: "Standard 6", clipType: "STANDARD", size: 6 },
  { id: "mock-standard-08", name: "Standard 8", clipType: "STANDARD", size: 8 },
  { id: "mock-curved-08", name: "Curved 8", clipType: "CURVED", size: 8 },
  { id: "mock-curved-10", name: "Curved 10", clipType: "CURVED", size: 10 },
];
export const MOCK_TREATMENT_OPTIONS = ["클립 결찰술", "코일 색전술", "치료 방법 미정"] as const;
export const MOCK_CURRENT_USER: CollaborationUser = { id: "local-clinician", name: "현재 사용자", role: "의료진" };
export const MOCK_INITIAL_MESSAGES: CollaborationMessage[] = [];
export const DEFAULT_CLIP_POSITION_Z = 50;
export const DEFAULT_CLIP_ROTATION: Vector3 = { x: 0, y: 0, z: 0 };
