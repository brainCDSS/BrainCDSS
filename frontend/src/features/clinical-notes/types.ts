export type ClinicalNoteStatus = "DRAFT" | "FINAL";

export interface ClinicalNote {
  noteId: string;
  encounterId: string;
  authorId: string;
  status: ClinicalNoteStatus;
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
  clinicalOpinion: string;
  finalizedAt: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface ClinicalNoteListResponse {
  count: number;
  next: string | number | null;
  previous: string | number | null;
  results: ClinicalNote[];
}

export interface ClinicalNoteApiItem {
  id?: string;
  note_id?: string;
  encounter_id?: string;
  author_id?: string;
  author?: { id?: string; user_id?: string } | string | null;
  status?: string;
  subjective?: string | null;
  objective?: string | null;
  assessment?: string | null;
  plan?: string | null;
  clinical_opinion?: string | null;
  finalized_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ClinicalNoteApiListResponse {
  count?: number;
  next?: string | number | null;
  previous?: string | number | null;
  results?: ClinicalNoteApiItem[];
}
