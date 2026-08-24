"""Validate repository JSON and required schema fields without network access."""
import json
from pathlib import Path
ROOT=Path(__file__).parents[2]
def load(path): return json.loads((ROOT/path).read_text(encoding="utf-8"))
def main():
    schemas=list((ROOT/"contracts").rglob("*.json")); [json.loads(p.read_text(encoding="utf-8")) for p in schemas]
    event=set(load("contracts/events/event-envelope.schema.json")["required"])
    assert event=={"event_id","event_type","event_version","occurred_at","trace_id","actor_id","aggregate_type","aggregate_id","payload"}
    required=set(load("contracts/model-bundle/model-bundle.schema.json")["required"])
    assert {"model_id","model_version","artifact_uri","checksum","framework","input_modalities","input_shape","preprocessing_version","postprocessing_version","output_type","created_at"}<=required
    print(f"OK: {len(schemas)} JSON contract files")
if __name__=="__main__": main()
