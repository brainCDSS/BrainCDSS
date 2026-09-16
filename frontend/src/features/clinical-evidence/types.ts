export type DiseaseType = "ischemic_stroke" | "intracranial_hemorrhage" | "intracranial_aneurysm";
export interface ClinicalEvidenceItem {
  pmid: string; title: string; journal: string; authors: string[]; publication_date: string | null;
  publication_year: number | null; publication_type: string[]; summary_short: string | null;
  summary_objective: string | null; summary_methods: string | null; summary_results: string | null;
  summary_clinical_significance: string | null; summary_limitations: string | null;
  summary_source: string; summary_model: string; summary_generated_at: string | null;
  summary_status: string; pubmed_url: string; doi: string | null; pmcid: string | null; display_rank: number;
}
export interface ClinicalEvidenceGroup { updated_at: string | null; disease: DiseaseType; items: ClinicalEvidenceItem[] }
export interface ClinicalEvidenceResponse { updated_at: string | null; disease: "all"; items: ClinicalEvidenceGroup[] }
