import { apiRequest } from "../../api/client";
import type {
  ClinicalNote,
  ClinicalNoteApiItem,
  ClinicalNoteApiListResponse,
  ClinicalNoteListResponse,
  ClinicalNoteStatus,
} from "./types";

function authorId(item: ClinicalNoteApiItem) {
  if (typeof item.author === "string") return item.author;
  return item.author_id ?? item.author?.id ?? item.author?.user_id ?? "";
}

function normalizeClinicalNote(item: ClinicalNoteApiItem): ClinicalNote {
  return {
    noteId: item.id ?? item.note_id ?? "",
    encounterId: item.encounter_id ?? "",
    authorId: authorId(item),
    status: item.status === "FINAL" ? "FINAL" : "DRAFT",
    subjective: item.subjective ?? "",
    objective: item.objective ?? "",
    assessment: item.assessment ?? "",
    plan: item.plan ?? "",
    clinicalOpinion: item.clinical_opinion ?? "",
    finalizedAt: item.finalized_at ?? null,
    createdAt: item.created_at ?? null,
    updatedAt: item.updated_at ?? null,
  };
}

export async function getClinicalNotes(
  encounterId: string,
  options: { status?: ClinicalNoteStatus; page?: number } = {},
): Promise<ClinicalNoteListResponse> {
  const query = new URLSearchParams({
    encounter_id: encounterId,
    page: String(options.page ?? 1),
  });
  if (options.status) query.set("status", options.status);
  const response = await apiRequest<ClinicalNoteApiListResponse>(
    `/api/v1/clinical-notes?${query.toString()}`,
  );
  const results = (response.results ?? [])
    .map(normalizeClinicalNote)
    .filter((item) => item.noteId);
  return {
    count: response.count ?? results.length,
    next: response.next ?? null,
    previous: response.previous ?? null,
    results,
  };
}

export async function getClinicalNote(noteId: string): Promise<ClinicalNote> {
  const response = await apiRequest<ClinicalNoteApiItem>(
    `/api/v1/clinical-notes/${encodeURIComponent(noteId)}`,
  );
  return normalizeClinicalNote(response);
}
