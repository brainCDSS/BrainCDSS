import { useEffect, useRef, useState } from "react";
import { Niivue } from "@niivue/niivue";
import { authenticatedAsset } from "../../api/client";
import { getNiftiViewerManifest } from "./api";

export default function NiftiViewer({ analysisId }: { analysisId: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [message, setMessage] = useState("NIfTI 영상을 불러오는 중입니다.");

  useEffect(() => {
    let active = true;
    const viewer = new Niivue({ show3Dcrosshair: true, backColor: [0, 0, 0, 1] });
    async function load() {
      const manifest = await getNiftiViewerManifest(analysisId);
      const canvas = canvasRef.current;
      if (!active || !canvas) return;
      const volumes = [
        ...manifest.inputs.slice(0, 1).map((item) => ({ ...authenticatedAsset(item.url), name: item.role, colormap: "gray", opacity: 1 })),
        ...manifest.masks.slice(0, 1).map((item) => ({ ...authenticatedAsset(item.url), name: "AI mask", colormap: "red", opacity: 0.55 })),
      ];
      if (!volumes.length) { setMessage("표시할 NIfTI 원본 또는 마스크가 없습니다."); return; }
      await viewer.attachToCanvas(canvas);
      await viewer.loadVolumes(volumes);
      if (active) setMessage("");
    }
    load().catch(() => { if (active) setMessage("NIfTI 영상을 불러오지 못했습니다."); });
    return () => { active = false; viewer.closeDrawing(); };
  }, [analysisId]);

  return <div className="nifti-viewer"><canvas ref={canvasRef} />{message && <div className="nifti-viewer__message">{message}</div>}</div>;
}
