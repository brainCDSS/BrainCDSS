// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ClinicalEvidencePanel } from "./ClinicalEvidencePanel";
import { getClinicalEvidence } from "./api";

vi.mock("./api", () => ({ getClinicalEvidence: vi.fn() }));
const article = { pmid: "123", title: "Clinical trial", journal: "Stroke", authors: [], publication_date: null,
  publication_year: 2026, publication_type: ["Randomized Controlled Trial"], summary_short: "짧은 요약",
  summary_objective: "목적", summary_methods: "방법", summary_results: "결과", summary_clinical_significance: "의미",
  summary_limitations: null, summary_source: "PUBMED_ABSTRACT", summary_model: "model", summary_generated_at: null,
  summary_status: "READY", pubmed_url: "https://pubmed.ncbi.nlm.nih.gov/123/", doi: null, pmcid: null, display_rank: 1 };
const response = { updated_at: null, disease: "all" as const, items: [
  { updated_at: null, disease: "ischemic_stroke" as const, items: [article] },
  { updated_at: null, disease: "intracranial_hemorrhage" as const, items: [] },
  { updated_at: null, disease: "intracranial_aneurysm" as const, items: [] }] };

describe("ClinicalEvidencePanel", () => {
  let host: HTMLDivElement;
  beforeEach(() => { (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true; host = document.createElement("div"); document.body.append(host); });
  afterEach(() => { host.remove(); vi.resetAllMocks(); });
  it("renders cards, switches all three tabs and expands stored summary", async () => {
    vi.mocked(getClinicalEvidence).mockResolvedValue(response);
    await act(async () => { createRoot(host).render(<ClinicalEvidencePanel />); });
    expect(host.textContent).toContain("Clinical trial");
    expect(host.querySelector('a[target="_blank"]')?.getAttribute("rel")).toBe("noopener noreferrer");
    const summary = Array.from(host.querySelectorAll("button")).find((button) => button.textContent === "요약 보기")!;
    act(() => summary.click()); expect(host.textContent).toContain("AI 요약 · PubMed Abstract 기반");
    for (const label of ["뇌출혈", "뇌동맥류"]) { const tab = Array.from(host.querySelectorAll("button")).find((button) => button.textContent === label)!;
      act(() => tab.click()); expect(host.textContent).toContain("표시할 임상 근거가 없습니다."); }
  });
  it("shows loading and isolated error states", async () => {
    let reject!: (reason?: unknown) => void; vi.mocked(getClinicalEvidence).mockReturnValue(new Promise((_, failure) => { reject = failure; }));
    act(() => createRoot(host).render(<ClinicalEvidencePanel />)); expect(host.textContent).toContain("불러오는 중");
    await act(async () => reject(new Error("offline"))); expect(host.textContent).toContain("불러오지 못했습니다");
  });
});
