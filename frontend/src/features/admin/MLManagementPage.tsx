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

type VersionFilter = "ALL" | MLModelVersionSummary["validation_status"] | "ACTIVE";
type DetailModal = "run" | "workflow" | "routing" | null;

const statusLabel: Record<MLModelVersionSummary["validation_status"], string> = {
  DRAFT: "DRAFT",
  VALIDATED: "VALIDATED",
  APPROVED: "APPROVED",
  RETIRED: "RETIRED",
};

const statusDescription: Record<MLModelVersionSummary["validation_status"], string> = {
  DRAFT: "등록됨 · 기술 검증 대기",
  VALIDATED: "기술 검증 완료 · 운영 승인 대기",
  APPROVED: "운영 사용 승인 완료",
  RETIRED: "사용 종료",
};

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "-" : date.toLocaleString("ko-KR");
}

function metricEntries(metrics: Record<string, unknown>) {
  return Object.entries(metrics)
    .filter(([key, value]) => key !== "_mlflow" && (typeof value === "number" || typeof value === "string"))
    .slice(0, 6);
}

function mlflowMetadata(metrics: Record<string, unknown>) {
  const raw = metrics._mlflow;
  if (!raw || typeof raw !== "object") {
    return { params: {} as Record<string, unknown>, tags: {} as Record<string, unknown> };
  }
  const metadata = raw as Record<string, unknown>;
  const params = metadata.params && typeof metadata.params === "object"
    ? metadata.params as Record<string, unknown>
    : {};
  const tags = metadata.tags && typeof metadata.tags === "object"
    ? metadata.tags as Record<string, unknown>
    : {};
  return { params, tags };
}

function displayValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export default function MLManagementPage() {
  const [overview, setOverview] = useState<MLModelOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [workingId, setWorkingId] = useState<string | null>(null);
  const [selectedModelId, setSelectedModelId] = useState("");
  const [selectedVersionId, setSelectedVersionId] = useState("");
  const [versionFilter, setVersionFilter] = useState<VersionFilter>("ALL");
  const [detailModal, setDetailModal] = useState<DetailModal>(null);
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

  const selectedModel = useMemo(
    () => overview?.models.find((item) => item.model_id === selectedModelId) ?? null,
    [overview, selectedModelId],
  );

  const selectedVersions = useMemo(
    () => overview?.versions.filter((item) => item.model_id === selectedModelId) ?? [],
    [overview, selectedModelId],
  );

  const filteredVersions = useMemo(
    () => selectedVersions.filter((item) => {
      if (versionFilter === "ALL") return true;
      if (versionFilter === "ACTIVE") return item.is_active;
      return item.validation_status === versionFilter;
    }),
    [selectedVersions, versionFilter],
  );

  const selectedVersion = useMemo(
    () => filteredVersions.find((item) => item.version_id === selectedVersionId)
      ?? filteredVersions[0]
      ?? null,
    [filteredVersions, selectedVersionId],
  );

  const approvedVersions = useMemo(
    () => overview?.versions.filter((item) => item.validation_status === "APPROVED") ?? [],
    [overview],
  );

  const activeRoutings = useMemo(
    () => overview?.routing_configs.filter((item) => item.is_active) ?? [],
    [overview],
  );

  const selectedVersionIsRouted = useMemo(
    () => Boolean(
      selectedVersion
      && activeRoutings.some(
        (routing) => routing.target_model_version?.version_id === selectedVersion.version_id,
      )
    ),
    [activeRoutings, selectedVersion],
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

  const filters: Array<{ key: VersionFilter; label: string }> = [
    { key: "ALL", label: "전체 " + selectedVersions.length },
    { key: "DRAFT", label: "DRAFT " + selectedVersions.filter((item) => item.validation_status === "DRAFT").length },
    { key: "VALIDATED", label: "VALIDATED " + selectedVersions.filter((item) => item.validation_status === "VALIDATED").length },
    { key: "APPROVED", label: "APPROVED " + selectedVersions.filter((item) => item.validation_status === "APPROVED").length },
    { key: "ACTIVE", label: "운영 " + selectedVersions.filter((item) => item.is_active).length },
  ];

  const metrics = selectedVersion ? metricEntries(selectedVersion.performance_metrics) : [];
  const metadata = selectedVersion
    ? mlflowMetadata(selectedVersion.performance_metrics)
    : { params: {}, tags: {} };

  const workflowIndex = selectedVersionIsRouted
    ? 3
    : selectedVersion?.validation_status === "APPROVED"
      ? 2
      : selectedVersion?.validation_status === "VALIDATED"
        ? 1
        : 0;

  const workflowSteps = [
    { title: "DRAFT", description: "MLflow Registry에서 동기화된 후보 모델 버전" },
    { title: "VALIDATED", description: "성능 지표·입출력 계약·추론 smoke test 등 기술 검증 완료" },
    { title: "APPROVED", description: "SYSTEM_ADMIN 운영 사용 승인 완료" },
    { title: "ROUTING", description: "승인된 모델 버전을 실제 분석 요청 라우팅에 활성화" },
  ];

  return <section className="clinical-page admin-page ml-management-page ml-management-page--viewport">
    <header className="clinical-page__heading ml-console-heading">
      <div>
        <h2>ML 관리</h2>
        <p>MLflow Registry 동기화부터 검증·승인·운영 라우팅까지 한 화면에서 관리합니다.</p>
      </div>
      <div className="ml-header-actions">
        <button
          type="button"
          className="admin-action admin-action--primary"
          disabled={loading || workingId === "mlflow-sync"}
          onClick={() => void syncMLflow()}
        >
          {workingId === "mlflow-sync" ? "동기화 중..." : "MLflow 동기화"}
        </button>
        <button type="button" className="admin-action" onClick={() => setDetailModal("routing")}>
          라우팅 관리
        </button>
        <button type="button" className="admin-action" disabled={loading} onClick={() => void load()}>
          새로고침
        </button>
      </div>
    </header>

    {error && <p className="admin-message admin-message--error ml-inline-message">{error}</p>}
    {syncResult && <p className={"admin-message ml-inline-message " + (syncResult.errors ? "admin-message--error" : "admin-message--success")}>
      발견 {syncResult.discovered} · 신규 {syncResult.created} · 업데이트 {syncResult.updated} · 건너뜀 {syncResult.skipped} · 오류 {syncResult.errors}
    </p>}

    {loading && <div className="clinical-card admin-table-empty">ML 관리 정보를 불러오는 중입니다.</div>}

    {!loading && overview && <div className="ml-viewport-body">
      <section className="clinical-card ml-routing-strip">
        <div className="ml-routing-strip__label">
          <strong>현재 운영 라우팅</strong>
          <span>{activeRoutings.length}개</span>
        </div>
        <div className="ml-routing-strip__items">
          {activeRoutings.map((routing) => <article key={routing.routing_id}>
            <strong>{routing.modality} · {routing.analysis_type}</strong>
            <span>{routing.target_model_version?.version ?? "-"}</span>
            <small>{routing.target_model_version?.model_name ?? "대상 없음"}</small>
          </article>)}
          {activeRoutings.length === 0 && <span className="ml-routing-strip__empty">활성화된 운영 라우팅이 없습니다.</span>}
        </div>
        <button type="button" className="admin-action" onClick={() => setDetailModal("routing")}>
          변경
        </button>
      </section>

      <div className="ml-workspace-grid">
        <aside className="clinical-card ml-model-rail">
          <div className="ml-compact-title">
            <strong>모델</strong>
            <span>{overview.models.length}</span>
          </div>
          <div className="ml-model-rail__list">
            {overview.models.map((model) => {
              const versions = overview.versions.filter((item) => item.model_id === model.model_id);
              const activeCount = versions.filter((item) => item.is_active).length;
              return <button
                key={model.model_id}
                type="button"
                className={"ml-model-rail__item " + (model.model_id === selectedModelId ? "is-active" : "")}
                onClick={() => {
                  setSelectedModelId(model.model_id);
                  setSelectedVersionId("");
                  setVersionFilter("ALL");
                }}
              >
                <span>{model.supported_modalities?.join("/") || "AI"}</span>
                <strong>{model.display_name}</strong>
                <small>{model.code}</small>
                <em>버전 {versions.length} · 운영 {activeCount}</em>
              </button>;
            })}
          </div>
        </aside>

        <section className="clinical-card ml-version-panel">
          <div className="ml-compact-title ml-version-panel__title">
            <div>
              <strong>모델 버전</strong>
              <span>{selectedModel?.display_name ?? "-"}</span>
            </div>
          </div>

          <div className="ml-version-filters ml-version-filters--compact">
            {filters.map((filter) => <button
              key={filter.key}
              type="button"
              className={versionFilter === filter.key ? "is-active" : ""}
              onClick={() => {
                setVersionFilter(filter.key);
                setSelectedVersionId("");
              }}
            >
              {filter.label}
            </button>)}
          </div>

          <div className="clinical-table-wrap ml-version-scroll">
            <table className="clinical-table ml-version-table ml-version-table--console">
              <thead>
                <tr>
                  <th>버전</th>
                  <th>MLflow Run</th>
                  <th>상태</th>
                  <th>성능</th>
                  <th>등록일</th>
                  <th>작업</th>
                </tr>
              </thead>
              <tbody>
                {filteredVersions.map((version) => (
                  <tr
                    key={version.version_id}
                    className={selectedVersion?.version_id === version.version_id ? "is-selected" : ""}
                    onClick={() => setSelectedVersionId(version.version_id)}
                  >
                    <td>
                      <strong>{version.version}</strong>
                      <small>MLflow v{version.mlflow_model_version || "-"}</small>
                    </td>
                    <td>
                      <strong className="ml-run-id-cell">{version.mlflow_run_id || "-"}</strong>
                      <small>{version.mlflow_registered_model_name || "-"}</small>
                    </td>
                    <td>
                      <span className={"ml-status is-" + version.validation_status.toLowerCase()}>{statusLabel[version.validation_status]}</span>
                      {version.is_active && <span className="ml-status is-active">운영</span>}
                    </td>
                    <td>{metricEntries(version.performance_metrics).slice(0, 2).map(([key, value]) => (
                      <small key={key}>{key}: {displayValue(value)}</small>
                    ))}{metricEntries(version.performance_metrics).length === 0 && "-"}</td>
                    <td>{formatDate(version.created_at)}</td>
                    <td onClick={(event) => event.stopPropagation()}>
                      <div className="ml-inline-actions">
                        {version.validation_status === "VALIDATED" && <button
                          type="button"
                          className="admin-action admin-action--primary"
                          disabled={workingId === version.version_id}
                          onClick={() => {
                            const reason = requestReason("사용 승인 사유를 입력하세요.");
                            if (reason) void run(version.version_id, () => approveMLModelVersion(version.version_id, reason));
                          }}
                        >
                          승인
                        </button>}
                        {!version.is_active && version.validation_status !== "RETIRED" && <button
                          type="button"
                          className="admin-action"
                          disabled={workingId === version.version_id}
                          onClick={() => {
                            const reason = requestReason("사용 종료 사유를 입력하세요.");
                            if (reason) void run(version.version_id, () => retireMLModelVersion(version.version_id, reason));
                          }}
                        >
                          종료
                        </button>}
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredVersions.length === 0 && <tr><td colSpan={6} className="admin-table-empty">조건에 맞는 모델 버전이 없습니다.</td></tr>}
              </tbody>
            </table>
          </div>
        </section>

        <aside className="clinical-card ml-version-detail ml-version-detail--compact">
          <div className="ml-compact-title">
            <strong>버전 상세</strong>
            {selectedVersion && <span className={"ml-status is-" + selectedVersion.validation_status.toLowerCase()}>
              {statusLabel[selectedVersion.validation_status]}
            </span>}
          </div>

          {!selectedVersion && <div className="admin-table-empty">확인할 모델 버전을 선택해 주세요.</div>}
          {selectedVersion && <div className="ml-version-detail__body">
            <div className="ml-detail-title ml-detail-title--compact">
              <div>
                <strong>{selectedVersion.version}</strong>
                <span>{selectedVersion.model_name}</span>
              </div>
              {selectedVersion.is_active && <span className="ml-status is-active">운영 중</span>}
            </div>

            <dl className="ml-detail-list ml-detail-list--compact">
              <div><dt>상태</dt><dd>{statusDescription[selectedVersion.validation_status]}</dd></div>
              <div><dt>MLflow 모델</dt><dd>{selectedVersion.mlflow_registered_model_name || "-"}</dd></div>
              <div><dt>MLflow Version</dt><dd>{selectedVersion.mlflow_model_version || "-"}</dd></div>
              <div><dt>Run ID</dt><dd className="ml-mono ml-break">{selectedVersion.mlflow_run_id || "-"}</dd></div>
              <div><dt>Artifact</dt><dd className="ml-mono ml-break">{selectedVersion.artifact_uri || "-"}</dd></div>
            </dl>

            <div className="ml-detail-metrics ml-detail-metrics--compact">
              {metrics.slice(0, 4).map(([key, value]) => <article key={key}>
                <span>{key}</span>
                <strong>{displayValue(value)}</strong>
              </article>)}
              {metrics.length === 0 && <p className="ml-section-caption">동기화된 성능 지표가 없습니다.</p>}
            </div>

            <div className="ml-detail-actions">
              <button type="button" className="admin-action admin-action--primary" onClick={() => setDetailModal("run")}>
                Run 상세
              </button>
              <button type="button" className="admin-action" onClick={() => setDetailModal("workflow")}>
                검증·승인
              </button>
            </div>
          </div>}
        </aside>
      </div>
    </div>}

    {detailModal === "run" && selectedVersion && <div className="admin-modal-backdrop" role="presentation" onMouseDown={() => setDetailModal(null)}>
      <section className="admin-modal ml-run-modal" role="dialog" aria-modal="true" aria-labelledby="ml-run-title" onMouseDown={(event) => event.stopPropagation()}>
        <header className="admin-modal__header">
          <div>
            <h3 id="ml-run-title">MLflow Run 상세 정보</h3>
            <p>BrainCDSS에 동기화되어 저장된 MLflow Run 메타데이터입니다.</p>
          </div>
          <button type="button" className="admin-action" onClick={() => setDetailModal(null)}>닫기</button>
        </header>

        <dl className="ml-detail-list">
          <div><dt>Registered Model</dt><dd>{selectedVersion.mlflow_registered_model_name || "-"}</dd></div>
          <div><dt>Model Version</dt><dd>{selectedVersion.mlflow_model_version || "-"}</dd></div>
          <div><dt>Run ID</dt><dd className="ml-mono">{selectedVersion.mlflow_run_id || "-"}</dd></div>
          <div><dt>Artifact URI</dt><dd className="ml-mono ml-break">{selectedVersion.artifact_uri || "-"}</dd></div>
        </dl>

        <div className="ml-run-section">
          <h4>Metrics</h4>
          <div className="ml-detail-metrics ml-detail-metrics--wide">
            {metricEntries(selectedVersion.performance_metrics).map(([key, value]) => <article key={key}>
              <span>{key}</span>
              <strong>{displayValue(value)}</strong>
            </article>)}
            {metricEntries(selectedVersion.performance_metrics).length === 0 && <p className="ml-section-caption">동기화된 metric이 없습니다.</p>}
          </div>
        </div>

        <div className="ml-run-columns">
          <div className="ml-run-section">
            <h4>Parameters</h4>
            <dl className="ml-kv-list">
              {Object.entries(metadata.params).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{displayValue(value)}</dd></div>)}
              {Object.keys(metadata.params).length === 0 && <p className="ml-section-caption">동기화된 parameter가 없습니다.</p>}
            </dl>
          </div>
          <div className="ml-run-section">
            <h4>Tags</h4>
            <dl className="ml-kv-list">
              {Object.entries(metadata.tags).map(([key, value]) => <div key={key}><dt>{key}</dt><dd className="ml-break">{displayValue(value)}</dd></div>)}
              {Object.keys(metadata.tags).length === 0 && <p className="ml-section-caption">동기화된 tag가 없습니다.</p>}
            </dl>
          </div>
        </div>

        <p className="ml-run-note">학습 epoch별 곡선은 현재 ModelVersion 동기화 데이터에 포함되지 않습니다. 필요하면 후속 단계에서 MLflow metric history 조회 API를 추가할 수 있습니다.</p>
      </section>
    </div>}

    {detailModal === "workflow" && selectedVersion && <div className="admin-modal-backdrop" role="presentation" onMouseDown={() => setDetailModal(null)}>
      <section className="admin-modal ml-workflow-modal" role="dialog" aria-modal="true" aria-labelledby="ml-workflow-title" onMouseDown={(event) => event.stopPropagation()}>
        <header className="admin-modal__header">
          <div>
            <h3 id="ml-workflow-title">모델 검증·승인 프로세스</h3>
            <p>{selectedVersion.model_name} / {selectedVersion.version}의 현재 운영 단계를 확인합니다.</p>
          </div>
          <button type="button" className="admin-action" onClick={() => setDetailModal(null)}>닫기</button>
        </header>

        {selectedVersion.validation_status === "RETIRED" && <p className="admin-message admin-message--error">이 모델 버전은 RETIRED 상태입니다.</p>}

        <ol className="ml-workflow-steps">
          {workflowSteps.map((step, index) => <li
            key={step.title}
            className={index < workflowIndex ? "is-complete" : index === workflowIndex ? "is-current" : ""}
          >
            <span className="ml-workflow-step__index">{index + 1}</span>
            <div>
              <strong>{step.title}</strong>
              <p>{step.description}</p>
            </div>
          </li>)}
        </ol>

        <p className="ml-run-note">MLflow 동기화는 모델을 자동 승인하거나 라우팅하지 않습니다. 검증, 운영 승인, 라우팅 전환은 각각 별도 절차로 진행됩니다.</p>
      </section>
    </div>}

    {detailModal === "routing" && <div className="admin-modal-backdrop" role="presentation" onMouseDown={() => setDetailModal(null)}>
      <section className="admin-modal ml-routing-modal" role="dialog" aria-modal="true" aria-labelledby="ml-routing-title" onMouseDown={(event) => event.stopPropagation()}>
        <header className="admin-modal__header">
          <div>
            <h3 id="ml-routing-title">운영 라우팅 관리</h3>
            <p>APPROVED 모델 버전으로 비활성 라우팅을 만든 뒤 운영 전환할 수 있습니다.</p>
          </div>
          <button type="button" className="admin-action" onClick={() => setDetailModal(null)}>닫기</button>
        </header>

        <div className="ml-routing-form ml-routing-form--modal">
          <label>라우팅 버전<input value={routingVersion} onChange={(event) => setRoutingVersion(event.target.value)} placeholder="예: ct-hemorrhage-2026-09" /></label>
          <label>영상 종류<select value={routingModality} onChange={(event) => setRoutingModality(event.target.value as "CT" | "MR" | "MRA")}><option value="CT">CT</option><option value="MR">MR</option><option value="MRA">MRA</option></select></label>
          <label>분석 유형<input value={routingAnalysisType} onChange={(event) => setRoutingAnalysisType(event.target.value)} placeholder="예: HEMORRHAGE" /></label>
          <label>대상 승인 버전<select value={routingTargetId} onChange={(event) => setRoutingTargetId(event.target.value)}><option value="">선택</option>{approvedVersions.map((version) => <option value={version.version_id} key={version.version_id}>{version.model_name} / {version.version}</option>)}</select></label>
          <label className="ml-routing-form__wide">변경 사유<input value={routingReason} onChange={(event) => setRoutingReason(event.target.value)} placeholder="예: 검증 완료 버전 운영 전환 준비" /></label>
          <button type="button" className="admin-action admin-action--primary" disabled={workingId === "routing-create"} onClick={() => void submitRouting()}>
            비활성 라우팅 생성
          </button>
        </div>

        <div className="clinical-table-wrap ml-routing-history">
          <table className="clinical-table">
            <thead><tr><th>라우팅</th><th>대상 모델</th><th>상태</th><th>생성일</th><th>작업</th></tr></thead>
            <tbody>
              {overview?.routing_configs.map((routing) => <tr key={routing.routing_id}>
                <td><strong>{routing.version}</strong><small>{routing.modality} · {routing.analysis_type}</small></td>
                <td>{routing.target_model_version ? routing.target_model_version.model_name + " / " + routing.target_model_version.version : "-"}</td>
                <td><span className={routing.is_active ? "ml-status is-approved" : "ml-status"}>{routing.is_active ? "운영 중" : "대기"}</span></td>
                <td>{formatDate(routing.created_at)}</td>
                <td>{!routing.is_active && <button
                  type="button"
                  className="admin-action admin-action--primary"
                  disabled={workingId === routing.routing_id}
                  onClick={() => {
                    const reason = requestReason("이 라우팅을 운영 전환하는 사유를 입력하세요.");
                    if (reason) void run(routing.routing_id, () => activateMLRoutingConfig(routing.routing_id, reason));
                  }}
                >
                  운영 전환
                </button>}</td>
              </tr>)}
              {overview?.routing_configs.length === 0 && <tr><td colSpan={5} className="admin-table-empty">등록된 라우팅이 없습니다.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>}
  </section>;
}
