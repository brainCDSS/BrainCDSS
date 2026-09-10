export type ViewerMode = "AXIAL" | "CORONAL" | "SAGITTAL" | "VESSEL_3D";
export type PlanningPanelTab = "planning" | "collaboration";
export type ClipType = "STANDARD" | "CURVED";
export interface Vector3 { x: number; y: number; z: number }
export interface VirtualClip { id: string; name: string; clipType: ClipType; size: number }
export interface PlacedClip { instanceId: string; clipId: string; clipType: ClipType; size: number; position: Vector3; rotation: Vector3 }
export interface PlanningCase {
  patient: { name: string; patientNo: string; sex: string; age: string };
  examination: { diagnosis: string; studyName: string; studyDate: string };
  assignment: { department: string; clinician: string; status: string };
  aiSummary: { finding: string; confidence: string; lesionLocation: string };
}
export interface CollaborationUser { id: string; name: string; role: string }
export interface ViewAttachment { viewerMode: ViewerMode; selectedClipInstanceId: string | null; placedClipCount: number }
export interface CollaborationMessage { id: string; sender: CollaborationUser; message: string; createdAt: string; attachment?: ViewAttachment }

// [추가] 수술·시술 플래닝 API 계약
export type SurgicalPlanStatus = "DRAFT" | "IN_PROGRESS" | "REVIEW_REQUESTED" | "CONFIRMED" | "CANCELLED";
export interface SurgicalPlanClipApi {
  id: string; planning_id: string; clip_id: string; clip_type: string; size: string;
  position_x: string; position_y: string; position_z: string;
  rotation_x: string; rotation_y: string; rotation_z: string;
  created_at: string; updated_at: string;
}
export interface SurgicalPlanApi {
  id: string; patient_id: string; encounter_id: string | null; study_id: string;
  ai_analysis_id: string | null; status: SurgicalPlanStatus; version: number;
  treatment_type: string; memo: string; created_by_id: string;
  finalized_by_id: string | null; created_at: string; updated_at: string;
  finalized_at: string | null; clips: SurgicalPlanClipApi[];
}
export interface SurgicalPlanMessageApi {
  id: string; planning_id: string; sender: CollaborationUser; message: string;
  viewer_state: Record<string, unknown>; created_at: string;
}
export interface SurgicalPlanListApi { count: number; results: SurgicalPlanApi[] }
export interface SurgicalPlanClipListApi { count: number; results: SurgicalPlanClipApi[] }
export interface SurgicalPlanMessageListApi { count: number; results: SurgicalPlanMessageApi[] }
export interface CreateSurgicalPlanRequest {
  patient_id: string; encounter_id?: string | null; study_id: string;
  ai_analysis_id?: string | null; treatment_type?: string; memo?: string;
}
export interface UpdateSurgicalPlanRequest {
  version: number; treatment_type?: string; memo?: string;
  status?: Exclude<SurgicalPlanStatus, "DRAFT" | "CONFIRMED">;
}
export type CreateSurgicalPlanClipRequest = Omit<SurgicalPlanClipApi, "id" | "planning_id" | "created_at" | "updated_at">;
export type UpdateSurgicalPlanClipRequest = Partial<Pick<SurgicalPlanClipApi, "position_x" | "position_y" | "position_z" | "rotation_x" | "rotation_y" | "rotation_z">>;
// [추가 끝] 수술·시술 플래닝 API 계약
