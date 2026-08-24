"""Fail on forbidden runtime architecture, artifacts, secrets or training folders."""
from pathlib import Path
ROOT=Path(__file__).parents[2]
def main():
    paths=[p for p in ROOT.rglob("*") if ".git" not in p.parts and "node_modules" not in p.parts]
    assert not [p for p in paths if p.is_dir() and p.name.lower() in {"ml","training","experiments","datasets"}]
    bad={".dcm",".dicom",".nii",".nrrd",".mha",".mhd",".pt",".pth",".ckpt",".onnx",".engine"}
    assert not [p for p in paths if p.is_file() and (p.suffix.lower() in bad or p.name.endswith(".nii.gz"))]
    word="red"+"is"
    assert not [p for p in [ROOT/"compose.yaml",ROOT/"backend/requirements/base.txt",ROOT/".env.example"] if word in p.read_text(encoding="utf-8").lower()]
    assert not [p for p in paths if p.is_file() and (p.name.startswith("service-account") or p.name in {"google-services.json","GoogleService-Info.plist"})]
    print("OK: repository safety policy")
if __name__=="__main__": main()
