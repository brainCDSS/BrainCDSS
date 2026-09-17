import { useEffect, useState } from "react";
import { getNiftiViewerManifest } from "../ai-analysis/api";
import { getStudyNiftiViewerManifest } from "../imaging/api";
import type { NiftiViewerManifest } from "../ai-analysis/types";
import { loadWasm } from "./wasm/loader";
import { assertAligned, loadVolume } from "./volume";
import type { LoadedViewer, WasmVolume } from "./types";

export function useRustViewer(analysisId?: string, studyId?: string) {
  const [manifest, setManifest] = useState<NiftiViewerManifest | null>(null);
  const [role, setRole] = useState("");
  const [loaded, setLoaded] = useState<LoadedViewer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    setManifest(null); setRole(""); setError(null); setLoading(true);
    const request = analysisId ? getNiftiViewerManifest(analysisId) : studyId ? getStudyNiftiViewerManifest(studyId) : Promise.reject(new Error("Study 또는 분석 ID가 필요합니다."));
    void request.then((data) => {
      if (!active) return;
      if (!data.inputs.length) throw new Error("원본 NIfTI가 없습니다.");
      setManifest(data); setRole(data.inputs.some((input) => input.role === "DWI") ? "DWI" : data.inputs[0].role);
    }).catch(() => { if (active) { setError("원본 영상 manifest를 불러오지 못했습니다."); setLoading(false); } });
    return () => { active = false; };
  }, [analysisId, studyId]);
  useEffect(() => {
    if (!manifest || !role) return;
    let active = true; let engine: WasmVolume | undefined;
    setLoaded(null); setError(null); setLoading(true);
    void (async () => {
      const { module, initMs } = await loadWasm();
      const start = performance.now();
      const input = manifest.inputs.find((item) => item.role === role);
      if (!input) throw new Error("선택한 채널의 원본 영상이 없습니다.");
      const [source, mask, probability] = await Promise.all([
        loadVolume(input.url, role),
        manifest.masks[0] ? loadVolume(manifest.masks[0].url, "mask") : undefined,
        manifest.probabilities?.[0] ? loadVolume(manifest.probabilities[0].url, "probability") : undefined,
      ]);
      if (!active) return;
      if (mask) assertAligned(source, mask);
      if (probability) assertAligned(source, probability);
      engine = new module.WasmVolume(...source.dimensions, source.voxels);
      if (mask) engine.set_mask(...mask.dimensions, mask.voxels);
      if (probability) engine.set_probability(...probability.dimensions, probability.voxels);
      setLoaded({ engine, source, mask, probability, wasmInitMs: initMs, volumeLoadMs: performance.now() - start });
      setLoading(false);
    })().catch(() => {
      if (active) { engine?.free(); engine = undefined; setError("Rust Viewer를 불러오지 못했습니다. WASM 빌드, 영상 접근 및 원본/오버레이 geometry를 확인하세요."); setLoading(false); }
    });
    return () => { active = false; engine?.free(); };
  }, [manifest, role]);
  return { loaded, loading, error, role, setRole, roles: manifest?.inputs.map((item) => item.role) ?? [] };
}
