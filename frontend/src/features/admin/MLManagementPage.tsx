import { useEffect, useMemo, useState } from "react";

import {
  activateMLRoutingConfig,
  approveMLModelVersion,
  createMLRoutingConfig,
  getMLModelOverview,
  retireMLModelVersion,
  syncMLflowModelVersions,
  validateMLModelVersion,
} from "./api";
import { ApiRequestError } from "../../api/client";
import type { MLModelOverview, MLModelVersionSummary, MLflowSyncResult, MLValidationCheck } from "./types";
import "./admin.css";

type VersionFilter = "ALL" | MLModelVersionSummary["validation_status"] | "ACTIVE";
type DetailModal = "run" | "workflow" | "routing" | null;

const mlflowUiUrl = import.meta.env.VITE_MLFLOW_UI_URL?.trim();

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
  const priority = [
    "standard.dice", "val_macro_dice_positive", "val_lesion_recall",
    "val_lesion_precision", "val_lesion_f1", "val_voxel_recall",
    "val_voxel_precision", "val_small_lesion_recall", "val_small_lesion_dice",
    "standard.lesion_recall", "standard.lesion_precision", "standard.lesion_f1",
    "standard.voxel_recall", "standard.voxel_precision", "standard.fp_per_case",
    "val_fp_per_scan", "val_negative_case_fp_rate",
  ];
  const priorityIndex = new Map(priority.map((key, index) => [key, index]));
  return Object.entries(metrics)
    .filter(([key, value]) => key !== "_mlflow" && key !== "epochs" && key !== "val_epoch" && key !== "val_positive_cases" && (typeof value === "number" || typeof value === "string"))
    .sort(([left], [right]) => (priorityIndex.get(left) ?? 999) - (priorityIndex.get(right) ?? 999))
    .slice(0, 8);
}

function trainingEntries(metrics: Record<string, unknown>) {
  return ["epochs", "val_epoch", "val_positive_cases"]
    .filter((key) => metrics[key] !== undefined)
    .map((key) => [key, metrics[key]] as [string, unknown]);
}

const metricLabels: Record<string, string> = {
  epochs: "학습 Epoch",
  val_epoch: "선택 Epoch",
  "standard.dice": "Dice",
  val_macro_dice_positive: "양성 Dice",
  val_positive_cases: "양성 Case",
  val_lesion_recall: "병변 Recall",
  val_lesion_precision: "병변 Precision",
  val_lesion_f1: "병변 F1",
  val_voxel_recall: "Voxel Recall",
  val_voxel_precision: "Voxel Precision",
  val_small_lesion_recall: "소병변 Recall",
  val_small_lesion_dice: "소병변 Dice",
  val_fp_per_scan: "Scan당 FP",
  val_negative_case_fp_rate: "음성 FP 비율",
};

function metricLabel(key: string) {
  return metricLabels[key] ?? key.replaceAll("_", " ");
}

function metricValue(value: unknown) {
  if (typeof value !== "number") return displayValue(value);
  if (Number.isInteger(value)) return value.toLocaleString("ko-KR");
  return value.toLocaleString("ko-KR", { maximumFractionDigits: 4 });
}

function modelModality(model: MLModelOverview["models"][number]) {
  if (model.display_name.toUpperCase().includes("MRA") || model.disease_scope === "ANEURYSM") return "MRA";
  if (model.display_name.toUpperCase().includes("DWI") || model.display_name.toUpperCase().includes("MRI")) return "MRI";
  return model.supported_modalities?.join("/") || "AI";
}

function modelClinicalName(model: MLModelOverview["models"][number]) {
  const name = model.display_name.toUpperCase();
  if (model.disease_scope === "ANEURYSM" || name.includes("ANEURYSM")) return "뇌동맥류";
  if (model.disease_scope.includes("HEMORRH") || name.includes("HEMORRH")) return "뇌출혈";
  if (model.disease_scope === "ISCHEMIC_STROKE" || model.display_name.toUpperCase().includes("ISCHEMIC")) return "뇌경색";
  return model.display_name;
}

function versionDisplayName(version: MLModelVersionSummary) {
  return version.experiment_id || mlflowMetadata(version.performance_metrics).experimentId || `Registry v${version.mlflow_model_version}`;
}

function mlflowMetadata(metrics: Record<string, unknown>) {
  const raw = metrics._mlflow;
  if (!raw || typeof raw !== "object") {
    return {
      params: {} as Record<string, unknown>,
      tags: {} as Record<string, unknown>,
      experimentId: "", modelBundleUri: "", manifestUri: "", checkpointUri: "",
    };
  }
  const metadata = raw as Record<string, unknown>;
  const params = metadata.params && typeof metadata.params === "object"
    ? metadata.params as Record<string, unknown>
    : {};
  const tagGroups = metadata.tags && typeof metadata.tags === "object"
    ? metadata.tags as Record<string, unknown> : {};
  const runTags = tagGroups.run && typeof tagGroups.run === "object"
    ? tagGroups.run as Record<string, unknown> : {};
  const versionTags = tagGroups.model_version && typeof tagGroups.model_version === "object"
    ? tagGroups.model_version as Record<string, unknown> : {};
  const tags = { ...runTags, ...versionTags };
  const text = (key: string) => typeof metadata[key] === "string" ? metadata[key] as string : "";
  const tagText = (key: string) => typeof tags[key] === "string" ? tags[key] as string : "";
  return {
    params,
    tags,
    experimentId: text("experiment_id") || tagText("experiment_id"),
    modelBundleUri: text("model_bundle_uri") || tagText("model_bundle_uri"),
    manifestUri: text("manifest_uri") || tagText("manifest_uri"),
    checkpointUri: text("checkpoint_uri") || tagText("checkpoint_uri"),
  };
}

const visibleTagKeys = [
  "analysis_type", "modality", "architecture", "dataset", "framework",
  "experiment_status", "lifecycle_status", "checkpoint_name", "source_git_commit",
];

function tagEntries(tags: Record<string, unknown>) {
  return visibleTagKeys.filter((key) => tags[key] !== undefined).map((key) => [key, tags[key]] as const);
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
  const [validationChecks, setValidationChecks] = useState<MLValidationCheck[] | null>(null);
  const [validationThreshold, setValidationThreshold] = useState("0.5");

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

  const activeRoutings = useMemo(
    () => overview?.routing_configs.filter((item) => item.is_active) ?? [],
    [overview],
  );

  const activeRoutingVersionIds = useMemo(
    () => new Set(
      activeRoutings
        .map((routing) => routing.target_model_version?.version_id)
        .filter((versionId): versionId is string => Boolean(versionId)),
    ),
    [activeRoutings],
  );

  const filteredVersions = useMemo(
    () => selectedVersions.filter((item) => {
      if (versionFilter === "ALL") return true;
      if (versionFilter === "ACTIVE") return activeRoutingVersionIds.has(item.version_id);
      return item.validation_status === versionFilter;
    }),
    [activeRoutingVersionIds, selectedVersions, versionFilter],
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

  const selectedVersionIsRouted = useMemo(
    () => Boolean(selectedVersion && activeRoutingVersionIds.has(selectedVersion.version_id)),
    [activeRoutingVersionIds, selectedVersion],
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

  const validateSelectedVersion = async () => {
    if (!selectedVersion) return;
    const reason = requestReason("기술 검증 실행 사유를 입력하세요.");
    if (!reason) return;
    const threshold = Number(validationThreshold);
    if (!Number.isFinite(threshold) || threshold < 0 || threshold > 1) {
      setError("운영 threshold는 0~1 사이 숫자로 입력해 주세요.");
      return;
    }
    setWorkingId(selectedVersion.version_id);
    setError(null);
    setValidationChecks(null);
    try {
      const result = await validateMLModelVersion(selectedVersion.version_id, reason, threshold);
      setValidationChecks(result.checks);
      await load();
    } catch (validationError) {
      if (validationError instanceof ApiRequestError) {
        try {
          const payload = JSON.parse(validationError.detail) as { checks?: MLValidationCheck[] };
          if (Array.isArray(payload.checks)) {
            setValidationChecks(payload.checks);
            return;
          }
        } catch { /* Use the generic message below. */ }
      }
      setError("기술 검증을 실행하지 못했습니다. 서버 연결과 관리자 권한을 확인해 주세요.");
    } finally {
      setWorkingId(null);
    }
  };

  const openWorkflow = (version: MLModelVersionSummary) => {
    const params = mlflowMetadata(version.performance_metrics).params;
    const threshold = Number(params.threshold);
    setValidationThreshold(Number.isFinite(threshold) && threshold >= 0 && threshold <= 1 ? String(threshold) : "0.5");
    setValidationChecks(null);
    setDetailModal("workflow");
  };

  const openRoutingForVersion = (version: MLModelVersionSummary) => {
    const tags = mlflowMetadata(version.performance_metrics).tags;
    const modality = String(tags.modality || "MR").toUpperCase();
    setRoutingTargetId(version.version_id);
    setRoutingModality(modality === "CT" ? "CT" : modality === "MRA" ? "MRA" : "MR");
    setRoutingAnalysisType(String(tags.analysis_type || ""));
    setRoutingVersion(`${versionDisplayName(version).toLowerCase()}-route`);
    setRoutingReason("");
    setDetailModal("routing");
  };

  const filters: Array<{ key: VersionFilter; label: string }> = [
    { key: "ALL", label: "전체 " + selectedVersions.length },
    { key: "DRAFT", label: "DRAFT " + selectedVersions.filter((item) => item.validation_status === "DRAFT").length },
    { key: "VALIDATED", label: "VALIDATED " + selectedVersions.filter((item) => item.validation_status === "VALIDATED").length },
    { key: "APPROVED", label: "APPROVED " + selectedVersions.filter((item) => item.validation_status === "APPROVED").length },
    { key: "ACTIVE", label: "운영 " + selectedVersions.filter((item) => activeRoutingVersionIds.has(item.version_id)).length },
  ];

  const metrics = selectedVersion ? metricEntries(selectedVersion.performance_metrics) : [];
  const metadata = selectedVersion
    ? mlflowMetadata(selectedVersion.performance_metrics)
    : { params: {}, tags: {}, experimentId: "", modelBundleUri: "", manifestUri: "", checkpointUri: "" };
  const training = selectedVersion ? trainingEntries(selectedVersion.performance_metrics) : [];

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
        {mlflowUiUrl && <a
          className="admin-action"
          href={mlflowUiUrl}
          target="_blank"
          rel="noopener noreferrer"
          title="인증된 MLflow 원본 화면을 새 탭에서 엽니다."
        >
          MLflow 원본 열기
        </a>}
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
              const activeCount = versions.filter((item) => activeRoutingVersionIds.has(item.version_id)).length;
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
                <span>{modelModality(model)}</span>
                <strong>{modelClinicalName(model)}</strong>
                <small>{model.display_name} · {model.code}</small>
                <em>버전 {versions.length} · 운영 {activeCount}</em>
              </button>;
            })}
          </div>
        </aside>

        <section className="clinical-card ml-version-panel">
          <div className="ml-compact-title ml-version-panel__title">
            <div>
              <strong>모델 버전</strong>
                <span>{selectedModel ? `${modelClinicalName(selectedModel)} · ${selectedModel.display_name}` : "-"}</span>
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
                      <strong>{versionDisplayName(version)}</strong>
                      <small>Registry v{version.mlflow_model_version || "-"} · DB {version.version}</small>
                    </td>
                    <td>
                      <strong className="ml-run-id-cell">{version.mlflow_run_id || "-"}</strong>
                      <small>{version.mlflow_registered_model_name || "-"}</small>
                    </td>
                    <td>
                      <span className={"ml-status is-" + version.validation_status.toLowerCase()}>{statusLabel[version.validation_status]}</span>
                      {activeRoutingVersionIds.has(version.version_id)
                        ? <span className="ml-status is-active">운영</span>
                        : version.is_active && <span className="ml-status">사용 가능</span>}
                    </td>
                    <td>{metricEntries(version.performance_metrics).slice(0, 2).map(([key, value]) => (
                      <small key={key}>{metricLabel(key)}: {metricValue(value)}</small>
                    ))}{metricEntries(version.performance_metrics).length === 0 && <small className="ml-metric-empty">성능 지표 미등록</small>}</td>
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
                          사용 종료
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
                <strong>{versionDisplayName(selectedVersion)}</strong>
                <span>{selectedVersion.model_name} · Registry v{selectedVersion.mlflow_model_version}</span>
              </div>
              {selectedVersionIsRouted
                ? <span className="ml-status is-active">운영 중</span>
                : selectedVersion.is_active && <span className="ml-status">사용 가능</span>}
            </div>

            <dl className="ml-detail-list ml-detail-list--compact">
              <div><dt>상태</dt><dd>{statusDescription[selectedVersion.validation_status]}</dd></div>
              <div><dt>실험 ID</dt><dd><strong>{versionDisplayName(selectedVersion)}</strong></dd></div>
              <div><dt>Registry</dt><dd>{selectedVersion.mlflow_registered_model_name || "-"} · v{selectedVersion.mlflow_model_version || "-"}</dd></div>
              <div><dt>Run ID</dt><dd className="ml-mono ml-ellipsis" title={selectedVersion.mlflow_run_id}>{selectedVersion.mlflow_run_id || "-"}</dd></div>
            </dl>

            <div className="ml-detail-metrics ml-detail-metrics--compact">
              {metrics.slice(0, 4).map(([key, value]) => <article key={key}>
                <span>{metricLabel(key)}</span>
                <strong>{metricValue(value)}</strong>
              </article>)}
              {metrics.length === 0 && <p className="ml-section-caption">평가용 성능 지표가 등록되지 않았습니다.</p>}
            </div>

            <div className="ml-detail-actions">
              <button type="button" className="admin-action admin-action--primary" onClick={() => setDetailModal("run")}>
                상세정보
              </button>
              <button type="button" className="admin-action" onClick={() => openWorkflow(selectedVersion)}>
                검증 · 승인
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
            <h3 id="ml-run-title">{versionDisplayName(selectedVersion)} 상세정보</h3>
            <p>{selectedVersion.model_name} · MLflow Registry v{selectedVersion.mlflow_model_version}</p>
          </div>
          <button type="button" className="admin-action" onClick={() => setDetailModal(null)}>닫기</button>
        </header>

        <dl className="ml-detail-list ml-run-identity">
          <div><dt>실험 ID</dt><dd><strong>{versionDisplayName(selectedVersion)}</strong></dd></div>
          <div><dt>Registered Model</dt><dd>{selectedVersion.mlflow_registered_model_name || "-"}</dd></div>
          <div><dt>Registry Version</dt><dd>v{selectedVersion.mlflow_model_version || "-"}</dd></div>
          <div><dt>Run ID</dt><dd className="ml-mono">{selectedVersion.mlflow_run_id || "-"}</dd></div>
          <div><dt>Artifact URI</dt><dd className="ml-mono ml-break">{selectedVersion.artifact_uri || "-"}</dd></div>
          <div><dt>Model Bundle</dt><dd className="ml-mono ml-break">{selectedVersion.model_bundle_uri || metadata.modelBundleUri || "-"}</dd></div>
          <div><dt>Manifest</dt><dd className="ml-mono ml-break">{selectedVersion.manifest_uri || metadata.manifestUri || "-"}</dd></div>
          <div><dt>Checkpoint</dt><dd className="ml-mono ml-break">{selectedVersion.checkpoint_uri || metadata.checkpointUri || "-"}</dd></div>
        </dl>

        <div className="ml-run-section">
          <h4>성능 지표 <span>Validation metrics</span></h4>
          <div className="ml-detail-metrics ml-detail-metrics--wide">
            {metricEntries(selectedVersion.performance_metrics).map(([key, value]) => <article key={key}>
              <span>{metricLabel(key)}</span>
              <strong>{metricValue(value)}</strong>
            </article>)}
            {metrics.length === 0 && <p className="ml-section-caption">이 Run에는 평가용 성능 지표가 없습니다. Epoch 정보는 학습 정보에서 확인할 수 있습니다.</p>}
          </div>
        </div>

        <div className="ml-run-section">
          <h4>학습 정보 <span>Training summary</span></h4>
          <div className="ml-training-summary">
            {training.map(([key, value]) => <article key={key}><span>{metricLabel(key)}</span><strong>{metricValue(value)}</strong></article>)}
            {training.length === 0 && <p className="ml-section-caption">동기화된 학습 요약이 없습니다.</p>}
          </div>
        </div>

        <div className="ml-run-columns">
          <div className="ml-run-section">
            <h4>학습 설정 <span>Parameters</span></h4>
            <dl className="ml-kv-list">
              {Object.entries(metadata.params).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{displayValue(value)}</dd></div>)}
              {Object.keys(metadata.params).length === 0 && <p className="ml-section-caption">동기화된 parameter가 없습니다.</p>}
            </dl>
          </div>
          <div className="ml-run-section">
            <h4>모델 메타데이터 <span>Tags</span></h4>
            <dl className="ml-kv-list">
              {tagEntries(metadata.tags).map(([key, value]) => <div key={key}><dt>{key}</dt><dd className="ml-break">{displayValue(value)}</dd></div>)}
              {tagEntries(metadata.tags).length === 0 && <p className="ml-section-caption">표시할 모델 태그가 없습니다.</p>}
            </dl>
          </div>
        </div>

        <p className="ml-run-note">현재 화면은 Registry 동기화 시점의 최종 지표를 표시합니다. Epoch별 학습 곡선은 MLflow metric history 연동 후 제공할 수 있습니다.</p>
      </section>
    </div>}

    {detailModal === "workflow" && selectedVersion && <div className="admin-modal-backdrop" role="presentation" onMouseDown={() => setDetailModal(null)}>
      <section className="admin-modal ml-workflow-modal" role="dialog" aria-modal="true" aria-labelledby="ml-workflow-title" onMouseDown={(event) => event.stopPropagation()}>
        <header className="admin-modal__header">
          <div>
            <h3 id="ml-workflow-title">모델 검증·승인 프로세스</h3>
            <p>{versionDisplayName(selectedVersion)} · {selectedVersion.model_name}</p>
          </div>
          <button type="button" className="admin-action" onClick={() => setDetailModal(null)}>닫기</button>
        </header>

        {selectedVersion.validation_status === "RETIRED" && <p className="admin-message admin-message--error">이 모델 버전은 RETIRED 상태입니다.</p>}

        <section className="ml-workflow-summary">
          <div><span>현재 상태</span><strong>{statusLabel[selectedVersion.validation_status]}</strong></div>
          <div><span>운영 라우팅</span><strong>{selectedVersionIsRouted ? "운영 중" : "미라우팅"}</strong></div>
          <div><span>성능 지표</span><strong>{metrics.length ? `${metrics.length}개` : "미등록"}</strong></div>
        </section>

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

        <section className="ml-readiness-card">
          <h4>다음 단계 안내</h4>
          {selectedVersion.validation_status === "DRAFT" && <p>현재 버전은 기술 검증 대기 상태입니다. Artifact와 성능 기준, 입출력 계약, smoke inference 검증이 완료되어야 VALIDATED로 전환할 수 있습니다.</p>}
          {selectedVersion.validation_status === "VALIDATED" && <p>기술 검증이 완료됐습니다. 운영 사용 승인 후 라우팅 대상으로 선택할 수 있습니다.</p>}
          {selectedVersion.validation_status === "APPROVED" && <p>운영 사용 승인이 완료됐습니다. 라우팅 관리에서 대상 버전으로 선택해 운영 전환할 수 있습니다.</p>}
          {selectedVersion.validation_status === "RETIRED" && <p>사용 종료된 버전으로 신규 승인이나 라우팅 전환을 할 수 없습니다.</p>}
        </section>

        {selectedVersion.validation_status === "DRAFT" && <label className="ml-validation-threshold">
          <span>운영 Threshold</span>
          <input type="number" min="0" max="1" step="0.01" value={validationThreshold} onChange={(event) => setValidationThreshold(event.target.value)} />
          <small>MLflow 값이 비어 있으면 기본 제안값 0.5를 검토 후 변경하세요.</small>
        </label>}

        {validationChecks && <section className="ml-validation-results">
          <h4>최근 기술 검증 결과</h4>
          <ul>
            {validationChecks.map((check) => <li className={check.passed ? "is-passed" : "is-failed"} key={check.code}>
              <span aria-hidden="true">{check.passed ? "✓" : "!"}</span>
              <div><strong>{check.label}</strong><p>{check.message}</p></div>
            </li>)}
          </ul>
        </section>}

        <div className="ml-workflow-actions">
          {selectedVersion.validation_status === "VALIDATED" && <button type="button" className="admin-action admin-action--primary" disabled={workingId === selectedVersion.version_id} onClick={() => {
            const reason = requestReason("사용 승인 사유를 입력하세요.");
            if (reason) void run(selectedVersion.version_id, () => approveMLModelVersion(selectedVersion.version_id, reason));
          }}>운영 사용 승인</button>}
          {selectedVersion.validation_status === "DRAFT" && <button type="button" className="admin-action admin-action--primary" disabled={workingId === selectedVersion.version_id} onClick={() => void validateSelectedVersion()}>{workingId === selectedVersion.version_id ? "검증 중..." : "기술 검증 실행"}</button>}
          {selectedVersion.validation_status === "APPROVED" && <button type="button" className="admin-action admin-action--primary" onClick={() => openRoutingForVersion(selectedVersion)}>라우팅 관리 열기</button>}
          <button type="button" className="admin-action" onClick={() => setDetailModal(null)}>닫기</button>
        </div>

        <p className="ml-run-note">MLflow 동기화만으로 승인이나 운영 라우팅이 자동 변경되지 않습니다.</p>
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
