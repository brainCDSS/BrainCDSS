// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import RustViewer from "./RustViewer";
import { useRustViewer } from "./useRustViewer";

vi.mock("./useRustViewer", () => ({ useRustViewer: vi.fn() }));
vi.mock("./RustViewerCanvas", () => ({ default: ({ settings }: { settings: { slice: number; maskOpacity: number } }) => <div data-testid="canvas">slice={settings.slice};mask={settings.maskOpacity}</div> }));
const source = { dimensions: [2,2,3] as [number,number,number], spacing:[1,1,1] as [number,number,number], affine:Array(16).fill(0), voxels:new Float32Array(12), voxelType:"Float32Array", window:80, level:40 };
const engine = { free:vi.fn(), set_mask:vi.fn(), set_probability:vi.fn(), extract_axial_slice:vi.fn(()=>new Float32Array(4)), window_slice:vi.fn(()=>new Uint8Array(4)), segmentation_slice:vi.fn(()=>new Uint8Array(16)), probability_slice:vi.fn(()=>new Uint8Array(16)), render_slice:vi.fn(()=>new Uint8Array(16)) };

describe("RustViewer", () => {
  let host: HTMLDivElement; let root: Root;
  beforeEach(() => { (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT:boolean }).IS_REACT_ACT_ENVIRONMENT=true; host=document.createElement("div");document.body.append(host);root=createRoot(host); });
  afterEach(() => { act(()=>root.unmount());host.remove();vi.resetAllMocks(); });
  it("renders loading and isolated error states", () => {
    vi.mocked(useRustViewer).mockReturnValue({ loaded:null,loading:true,error:null,role:"",setRole:vi.fn(),roles:[] }); act(()=>root.render(<RustViewer analysisId="a"/>)); expect(host.textContent).toContain("준비하는 중");
    vi.mocked(useRustViewer).mockReturnValue({ loaded:null,loading:false,error:"WASM 실패",role:"",setRole:vi.fn(),roles:[] }); act(()=>root.render(<RustViewer analysisId="a"/>)); expect(host.textContent).toContain("WASM 실패");
  });
  it("changes slice and segmentation visibility", () => {
    vi.mocked(useRustViewer).mockReturnValue({ loaded:{engine,source,mask:source,wasmInitMs:1,volumeLoadMs:2},loading:false,error:null,role:"CT",setRole:vi.fn(),roles:["CT"] }); act(()=>root.render(<RustViewer analysisId="a"/>));
    const slice=host.querySelector('input[aria-label="slice"]') as HTMLInputElement | null;
    expect(host.textContent).toContain("2 / 3");
    expect(slice).not.toBeNull();
    const checkbox=host.querySelector('input[type="checkbox"]') as HTMLInputElement; act(()=>checkbox.click()); expect(host.querySelector('[data-testid="canvas"]')?.textContent).toContain("mask=0");
  });
});
