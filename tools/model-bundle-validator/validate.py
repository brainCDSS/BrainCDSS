"""Validate a model manifest against the repository schema without loading artifacts."""
import argparse,json,sys
from pathlib import Path
def main():
    p=argparse.ArgumentParser(); p.add_argument("manifest",type=Path); p.add_argument("--schema",type=Path,default=Path(__file__).parents[2]/"contracts/model-bundle/model-bundle.schema.json"); a=p.parse_args()
    try:
        import jsonschema; jsonschema.validate(json.loads(a.manifest.read_text()),json.loads(a.schema.read_text()))
    except ImportError: print("NOT_IMPLEMENTED: install jsonschema to validate",file=sys.stderr); return 2
    except Exception as e: print(f"INVALID: {e}",file=sys.stderr); return 1
    print("VALID"); return 0
if __name__=="__main__": raise SystemExit(main())
