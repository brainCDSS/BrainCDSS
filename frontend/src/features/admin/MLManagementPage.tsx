import { useEffect, useMemo, useState } from "react";

import {
  activateMLRoutingConfig,
  approveMLModelVersion,
  createMLRoutingConfig,
  getMLModelOverview,
  retireMLModelVersion,
  syncMLflowModelVersions,
} from "./api";
import type { MLModelOverview, MLModelVersionSummary, MLflowSyncResult } from "./types";
import "./admin.css";

const statusLabel: Record<MLModelVersionSummary["validation_status"], string> = {
  DRAFT: "등록됨",
  VALIDATED: "기술 검증 완료",
  APPROVED: "사용 승인",
  RETIRED: "사용 종료",
};

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "-" : date.toLocaleString("ko-KR");
}

function metricSummary(metrics: Record<string, unknown>) {
  return Object.entries(metrics).slice(0, 2).map(([key, value]) => `${key}: ${String(value)}`).join(" · ") || "-";
}

export default function MLManagementPage() {
  const [overview, setOverview] = useState<MLModelOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [workingId, setWorkingId] = useState<string | null>(null);
  const [selectedModelId, setSelectedModelId] = useState("");
  const [routingVersion, setRoutingVersion] = useState("");
  const [routingModality, setRoutingModality] = useState<"CT" | "MR" | "MRA">("MRA");
  const [routingAnalysisType, setRoutingAnalysisType] = useState("");
  const [routingTargetId, setRoutingTargetId] = useState("");
  const [routingReason, setRoutingReason] = useState("");
  const [syncResult, setSyncResult] = useState<MLflowSyncResult | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getMLModelOverview();
      setOverview(data);
      setSelectedModelId((current) => current || data.models[0]?.model_id || "");
    } catch {
      setError("ML 관리 정보를 불러오지 못했습니다. 관리자 권한과 백엔드 연결을 확인해 주세요.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const selectedVersions = useMemo(
    () => overview?.versions.filter((item) => item.model_id === selectedModelId) ?? [],
    [overview, selectedModelId],
  );
  const approvedVersions = useMemo(
    () => overview?.versions.filter((item) => item.validation_status === "APPROVED") ?? [],
    [overview],
  );

  const run = async (id: string, action: () => Promise<unknown>) => {
    setWorkingId(id);
    setError(null);
    try {
      await action();
      await load();
    } catch {
      setError("요청을 처리하지 못했습니다. 상태와 입력한 사유를 다시 확인해 주세요.");
    } finally {
      setWorkingId(null);
    }
  };

  const requestReason = (message: string) => {
    const value = window.prompt(message);
    return value?.trim() || null;
  };

  const syncMLflow = async () => {
    setWorkingId("mlflow-sync");
    setError(null);
    setSyncResult(null);
    try {
      const result = await syncMLflowModelVersions();
      setSyncResult(result);
      await load();
    } catch {
      setError("MLflow 동기화에 실패했습니다. Cloud Run 연결 및 관리자 권한을 확인해 주세요.");
    } finally {
      setWorkingId(null);
    }
  };

  const submitRouting = async () => {
    if (!routingVersion.trim() || !routingAnalysisType.trim() || !routingTargetId || !routingReason.trim()) {
      setError("라우팅 버전, 분석 유형, 대상 모델 버전, 변경 사유를 모두 입력해 주세요.");
      return;
    }
    await run("routing-create", async () => {
      await createMLRoutingConfig({
        version: routingVersion.trim(),
        modality: routingModality,
        analysis_type: routingAnalysisType.trim(),
        target_model_version_id: routingTargetId,
        reason: routingReason.trim(),
      });
      setRoutingVersion("");
      setRoutingAnalysisType("");
      setRoutingTargetId("");
      setRoutingReason("");
    });
  };

  return <section className="clinical-page admin-page ml-management-page">
    <header className="clinical-page__heading">
      <div>
        <h2>ML 관리</h2>
        <p>운영 모델 버전과 AI 라우팅을 관리합니다. MLflow 원본 등록·학습은 여기서 수행하지 않습니다.</p>
      </div>
      <div className="ml-header-actions">
        <button type="button" className="admin-action admin-action--primary" disabled={loading || workingId === "mlflow-sync"} onClick={() => void syncMLflow()}>{workingId === "mlflow-sync" ? "동기화 중..." : "MLflow 동기화"}</button>
        <button type="button" className="admin-action" disabled={loading} onClick={() => void load()}>새로고침</button>
      </div>
    </header>

    {error && <p className="admin-message admin-message--error">{error}</p>}
    {syncResult && <p className={`admin-message ${syncResult.errors ? "admin-message--error" : "admin-message--success"}`}>발견 {syncResult.discovered} / 신규 {syncResult.created} / 업데이트 {syncResult.updated} / 건너뜀 {syncResult.skipped} / 오류 {syncResult.errors}</p>}
    {loading && <div className="clinical-card admin-table-empty">ML 관리 정보를 불러오는 중입니다.</div>}

    {!loading && overview && <>
      <section className="clinical-card ml-current-routing">
        <div className="clinical-card__title"><h3>현재 운영 라우팅</h3></div>
        <div className="ml-routing-grid">
          {overview.routing_configs.filter((item) => item.is_active).map((item) => (
            <article key={item.routing_id}>
              <strong>{item.modality} · {item.analysis_type}</strong>
              <span>{item.target_model_version?.model_name ?? "대상 없음"} / {item.target_model_version?.version ?? "-"}</span>
              <small>라우팅 {item.version}</small>
            </article>
          ))}
          {overview.routing_configs.every((item) => !item.is_active) && <p className="admin-table-empty">활성화된 라우팅이 없습니다.</p>}
        </div>
      </section>

      <section className="clinical-card">
        <div className="clinical-card__title"><h3>모델 및 버전</h3></div>
        <div className="ml-model-tabs">
          {overview.models.map((model) => <button key={model.model_id} type="button" className={model.model_id === selectedModelId ? "is-active" : ""} onClick={() => setSelectedModelId(model.model_id)}>{model.display_name}</button>)}
        </div>
        <div className="clinical-table-wrap"><table className="clinical-table ml-version-table"><thead><tr><th>버전</th><th>MLflow</th><th>검증 상태</th><th>운영 가능</th><th>성능 지표</th><th>등록일</th><th>작업</th></tr></thead><tbody>
          {selectedVersions.map((version) => <tr key={version.version_id}><td><strong>{version.version}</strong><small>{version.model_code}</small></td><td>{version.mlflow_registered_model_name}<small>v{version.mlflow_model_version} · run {version.mlflow_run_id || "-"}</small></td><td><span className={`ml-status is-${version.validation_status.toLowerCase()}`}>{statusLabel[version.validation_status]}</span></td><td>{version.is_active ? "활성" : "비활성"}</td><td>{metricSummary(version.performance_metrics)}</td><td>{formatDate(version.created_at)}</td><td><div className="ml-inline-actions">
            {version.validation_status === "VALIDATED" && <button type="button" className="admin-action admin-action--primary" disabled={workingId === version.version_id} onClick={() => { const reason = requestReason("사용 승인 사유를 입력하세요."); if (reason) void run(version.version_id, () => approveMLModelVersion(version.version_id, reason)); }}>승인</button>}
            {!version.is_active && version.validation_status !== "RETIRED" && <button type="button" className="admin-action" disabled={workingId === version.version_id} onClick={() => { const reason = requestReason("사용 종료 사유를 입력하세요."); if (reason) void run(version.version_id, () => retireMLModelVersion(version.version_id, reason)); }}>종료</button>}
          </div></td></tr>)}
          {selectedVersions.length === 0 && <tr><td colSpan={7} className="admin-table-empty">등록된 모델 버전이 없습니다.</td></tr>}
        </tbody></table></div>
      </section>

      <section className="clinical-card">
        <div className="clinical-card__title"><h3>라우팅 생성 및 전환</h3></div>
        <div className="ml-routing-form">
          <label>라우팅 버전<input value={routingVersion} onChange={(event) => setRoutingVersion(event.target.value)} placeholder="예: mra-aneurysm-2026-10" /></label>
          <label>영상 종류<select value={routingModality} onChange={(event) => setRoutingModality(event.target.value as "CT" | "MR" | "MRA")}><option value="CT">CT</option><option value="MR">MR</option><option value="MRA">MRA</option></select></label>
          <label>분석 유형<input value={routingAnalysisType} onChange={(event) => setRoutingAnalysisType(event.target.value)} placeholder="예: ANEURYSM" /></label>
          <label>대상 승인 버전<select value={routingTargetId} onChange={(event) => setRoutingTargetId(event.target.value)}><option value="">선택</option>{approvedVersions.map((version) => <option value={version.version_id} key={version.version_id}>{version.model_name} / {version.version}</option>)}</select></label>
          <label className="ml-routing-form__wide">변경 사유<input value={routingReason} onChange={(event) => setRoutingReason(event.target.value)} placeholder="예: 검증 완료 버전 운영 전환 준비" /></label>
          <button type="button" className="admin-action" disabled={workingId === "routing-create"} onClick={() => void submitRouting()}>비활성 라우팅 생성</button>
        </div>
        <div className="clinical-table-wrap"><table className="clinical-table"><thead><tr><th>라우팅</th><th>대상 모델</th><th>상태</th><th>생성일</th><th>작업</th></tr></thead><tbody>
          {overview.routing_configs.map((routing) => <tr key={routing.routing_id}><td><strong>{routing.version}</strong><small>{routing.modality} · {routing.analysis_type}</small></td><td>{routing.target_model_version ? `${routing.target_model_version.model_name} / ${routing.target_model_version.version}` : "-"}</td><td><span className={routing.is_active ? "ml-status is-approved" : "ml-status"}>{routing.is_active ? "운영 중" : "대기"}</span></td><td>{formatDate(routing.created_at)}</td><td>{!routing.is_active && <button type="button" className="admin-action admin-action--primary" disabled={workingId === routing.routing_id} onClick={() => { const reason = requestReason("이 라우팅을 운영 전환하는 사유를 입력하세요."); if (reason) void run(routing.routing_id, () => activateMLRoutingConfig(routing.routing_id, reason)); }}>운영 전환</button>}</td></tr>)}
          {overview.routing_configs.length === 0 && <tr><td colSpan={5} className="admin-table-empty">등록된 라우팅이 없습니다.</td></tr>}
        </tbody></table></div>
      </section>
    </>}
  </section>;
}
