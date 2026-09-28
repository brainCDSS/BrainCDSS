// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AIAnalysisResultsPage from "./AIAnalysisResultsPage";
import { getAIAnalyses, getAIAnalysisResult } from "./api";
import { getImagingStudy } from "../imaging/api";

vi.mock("./api", () => ({ getAIAnalyses:vi.fn(), getAIAnalysis:vi.fn(), getAIAnalysisResult:vi.fn(), createAIResultReview:vi.fn() }));
vi.mock("../imaging/api", () => ({ getImagingStudy:vi.fn() }));
vi.mock("./NiftiViewer", () => ({ default:()=> <div data-viewer="existing">existing</div> }));

describe("AI analysis viewer", () => {
  let host:HTMLDivElement;
  beforeEach(async()=>{(globalThis as typeof globalThis&{IS_REACT_ACT_ENVIRONMENT:boolean}).IS_REACT_ACT_ENVIRONMENT=true;host=document.createElement("div");document.body.append(host);
    vi.mocked(getAIAnalyses).mockResolvedValue({count:1,results:[{analysis_id:"a",study_id:"s",analysis_type:"CEREBRAL_ANEURYSM_MRA",status:"COMPLETED",stage:"DONE",priority:"NORMAL",attempt_count:1,requested_at:"2026-01-01"}]});
    vi.mocked(getAIAnalysisResult).mockResolvedValue({analysis_id:"a",result_id:"r",output_schema_version:"1",is_positive:true,confidence:.8,threshold_used:.5,lesion_count:1,total_volume_ml:1,severity:"UNREVIEWED",structured_findings:{},artifacts:[]});
    vi.mocked(getImagingStudy).mockResolvedValue({study_id:"s",accession_number:"A",study_datetime:"2026-01-01",modalities:["MR"],status:"AVAILABLE",series_count:1,instance_count:1,latest_analysis:null,current_report:null,critical_finding:false,series:[],patient:null} as never);
  });
  afterEach(()=>{host.remove();vi.resetAllMocks();});
  it("shows the clinical NIfTI viewer without an experimental viewer selector",async()=>{await act(async()=>{createRoot(host).render(<AIAnalysisResultsPage/>);});expect(host.querySelector('[data-viewer="existing"]')).not.toBeNull();expect(host.textContent).not.toContain("Rust Viewer");});
});
