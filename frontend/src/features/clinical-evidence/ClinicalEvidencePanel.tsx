import { useEffect, useMemo, useState } from "react";
import { getClinicalEvidence } from "./api";
import type { ClinicalEvidenceGroup, ClinicalEvidenceItem, DiseaseType } from "./types";
import "./clinical-evidence.css";

export const EVIDENCE_TABS: Array<{ key: DiseaseType; label: string }> = [
  { key: "ischemic_stroke", label: "뇌경색" }, { key: "intracranial_hemorrhage", label: "뇌출혈" },
  { key: "intracranial_aneurysm", label: "뇌동맥류" },
];
const safePubmedUrl = (item: ClinicalEvidenceItem) => /^[1-9][0-9]{0,15}$/.test(item.pmid)
  && item.pubmed_url === `https://pubmed.ncbi.nlm.nih.gov/${item.pmid}/` ? item.pubmed_url : null;
const safePmcUrl = (pmcid: string | null) => pmcid && /^PMC[1-9][0-9]{0,20}$/.test(pmcid)
  ? `https://pmc.ncbi.nlm.nih.gov/articles/${pmcid}/` : null;
const DISPLAY_TYPES = ["Practice Guideline", "Guideline", "Meta-Analysis", "Systematic Review",
  "Randomized Controlled Trial", "Clinical Trial", "Multicenter Study", "Observational Study", "Review"];
const displayType = (item: ClinicalEvidenceItem) => DISPLAY_TYPES.find((value) => item.publication_type.includes(value))
  ?? item.publication_type[0] ?? "Clinical Study";

function Summary({ item }: { item: ClinicalEvidenceItem }) {
  if (item.summary_status !== "READY") return <p className="evidence-summary-pending">요약 준비 중입니다. PubMed 원문을 확인해 주세요.</p>;
  const rows = [["연구 목적", item.summary_objective], ["대상 및 방법", item.summary_methods],
    ["주요 결과", item.summary_results], ["임상적 의미", item.summary_clinical_significance], ["제한사항", item.summary_limitations]];
  return <div className="evidence-summary"><strong>AI 요약 · PubMed Abstract 기반</strong><p>{item.summary_short}</p>
    <dl>{rows.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value ?? "정보 없음"}</dd></div>)}</dl>
    <small>참고용 요약이며 원문과 임상 지침을 대체하지 않습니다.</small></div>;
}

export function ClinicalEvidencePanel() {
  const [groups, setGroups] = useState<ClinicalEvidenceGroup[]>([]);
  const [active, setActive] = useState<DiseaseType>("ischemic_stroke");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  useEffect(() => { let mounted = true; setLoading(true); setError(false);
    void getClinicalEvidence().then((response) => { if (mounted) setGroups(response.items); })
      .catch(() => { if (mounted) setError(true); }).finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, []);
  const group = useMemo(() => groups.find((entry) => entry.disease === active), [groups, active]);
  const updated = group?.updated_at ? new Date(group.updated_at).toLocaleString("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }) : null;
  return <article className="dash-evidence dash-chart-card"><header><h3>최신 임상 근거</h3><span>PubMed</span></header>
    <nav aria-label="질환별 임상 근거">{EVIDENCE_TABS.map((tab) => <button key={tab.key} type="button" className={active === tab.key ? "is-active" : ""}
      aria-pressed={active === tab.key} onClick={() => { setActive(tab.key); setExpanded(null); }}>{tab.label}</button>)}</nav>
    <div className="evidence-list">
      {loading && <div className="evidence-state">최신 근거를 불러오는 중입니다.</div>}
      {!loading && error && <div className="evidence-state is-error">임상 근거를 불러오지 못했습니다.<br />기존 진료 화면은 계속 사용할 수 있습니다.</div>}
      {!loading && !error && !group?.items.length && <div className="evidence-state">표시할 임상 근거가 없습니다.</div>}
      {!loading && !error && group?.items.map((item) => { const pubmed = safePubmedUrl(item); const pmc = safePmcUrl(item.pmcid); const open = expanded === item.pmid;
        return <section className="evidence-item" key={item.pmid}><span className="evidence-badge">{displayType(item)}</span>
          <h4>{item.title}</h4><p>{item.journal || "Journal 정보 없음"} · {item.publication_year ?? "연도 정보 없음"}</p>
          <div className="evidence-actions"><button type="button" aria-expanded={open} onClick={() => setExpanded(open ? null : item.pmid)}>{open ? "요약 닫기" : "요약 보기"}</button>
            {pubmed && <a href={pubmed} target="_blank" rel="noopener noreferrer">PubMed ↗</a>}
            {pmc && <a href={pmc} target="_blank" rel="noopener noreferrer">Full Text ↗</a>}</div>{open && <Summary item={item} />}</section>;
      })}
    </div>{updated && <footer>마지막 업데이트 {updated}</footer>}
  </article>;
}
