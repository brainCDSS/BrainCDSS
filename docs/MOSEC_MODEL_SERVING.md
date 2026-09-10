# MOSEC model serving layout

The public Cloud Run port is owned by the FastAPI contract gateway. The same
container starts an internal MOSEC server on loopback. The gateway validates the
shared request schema and routes by `analysis_type`:

| Analysis type | MOSEC route | Worker |
| --- | --- | --- |
| `HEMORRHAGIC_STROKE_CT` | `/v1/models/hemorrhage` | `HemorrhageWorker` |
| `ISCHEMIC_STROKE_DWI_ADC` | `/v1/models/ischemia` | `IschemiaWorker` |
| `CEREBRAL_ANEURYSM_MRA` | `/v1/models/aneurysm` | `AneurysmWorker` |

MOSEC owns the model worker processes. FastAPI remains the stable authenticated
API boundary used by Django and can fall back to `MODEL_SERVING_BACKEND=direct`
for tests and incident recovery. MOSEC is loopback-only and is not exposed as a
second Cloud Run port.

`MOSEC_ENABLED_MODELS` controls which workers a deployment starts. If all three
models do not fit in one GPU, deploy the same image as three model-specific
services with one enabled model each. This preserves one codebase and the same
HTTP contract while isolating GPU memory and scaling.

Useful environment variables:

- `MODEL_SERVING_BACKEND=mosec`
- `MOSEC_URL=http://127.0.0.1:8101`
- `MOSEC_PORT=8101`
- `MOSEC_ENABLED_MODELS=hemorrhage,ischemia,aneurysm`
- `MOSEC_WORKER_TIMEOUT_SECONDS=1800`
- `MOSEC_REQUEST_TIMEOUT_SECONDS=1800`

The initial configuration deliberately uses `max_batch_size=1` because 3D
medical volumes vary in shape and GPU memory use. MOSEC metrics should be used
to justify later batching changes.
