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
