import { apiRequest } from "../../api/client";
import { filterAssessmentItemsForDisplay } from "../assessments/viewModel";
import type {
  ClinicalNote,
  ClinicalNoteApiItem,
  ClinicalNoteApiListResponse,
  ClinicalNoteDraftFields,
  ClinicalNoteListResponse,
  ClinicalNoteStatus,
  CreateClinicalNoteRequest,
  InitialAssessmentEncounterResponse,
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

export async function createClinicalNote(
  payload: CreateClinicalNoteRequest,
): Promise<ClinicalNote> {
  const response = await apiRequest<ClinicalNoteApiItem>("/api/v1/clinical-notes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      encounter_id: payload.encounterId,
      subjective: payload.subjective,
      objective: payload.objective,
      assessment: payload.assessment,
      plan: payload.plan,
    }),
  });
  return normalizeClinicalNote(response);
}

export async function updateClinicalNote(
  noteId: string,
  fields: ClinicalNoteDraftFields,
): Promise<ClinicalNote> {
  const response = await apiRequest<ClinicalNoteApiItem>(
    `/api/v1/clinical-notes/${encodeURIComponent(noteId)}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        subjective: fields.subjective,
        objective: fields.objective,
        assessment: fields.assessment,
        plan: fields.plan,
        clinical_opinion: fields.clinicalOpinion,
      }),
    },
  );
  return normalizeClinicalNote(response);
}

export async function finalizeClinicalNote(noteId: string): Promise<ClinicalNote> {
  const response = await apiRequest<ClinicalNoteApiItem>(
    `/api/v1/clinical-notes/${encodeURIComponent(noteId)}/finalize`,
    { method: "POST" },
  );
  return normalizeClinicalNote(response);
}

export async function getInitialAssessmentsByEncounter(
  encounterId: string,
): Promise<InitialAssessmentEncounterResponse> {
  const query = new URLSearchParams({
    encounter_id: encounterId,
  });

  const response =
    await apiRequest<InitialAssessmentEncounterResponse>(
      `/api/v1/assessments?${query.toString()}`,
    );

  return {
    ...response,
    results: (response.results ?? []).map(
      (assessment) => ({
        ...assessment,
        items:
          filterAssessmentItemsForDisplay(
            assessment.items,
          ),
      }),
    ),
  };
}
