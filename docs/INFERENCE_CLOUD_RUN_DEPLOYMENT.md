# brainon-inference 배포

현재 서비스는 하나의 비공개 Cloud Run GPU 서비스 `brainon-inference`로 배포한다. FastAPI가 요청 검증, GCS 입출력, 모델 캐시와 nnU-Net 실행을 담당한다.

## 사전 값

- 실제 Google Cloud 프로젝트 ID
- Artifact Registry 저장소 이름
- 환자별 추론 산출물을 저장할 별도 비공개 GCS 버킷
- Cloud Run 서비스 계정

모델 입력은 `gs://brainon-cdss-models`에서 읽는다. 결과 버킷은 모델 버킷과 분리하고 Uniform bucket-level access와 Public access prevention을 켠다.

## 이미지 빌드와 배포

아래 값을 실제 환경에 맞게 지정한다. GPU 종류, 리전과 가용성은 프로젝트 할당량에 맞춰 조정한다.

비공개 모델 저장소는 먼저 로컬 wheel로 패키징한다. 이 파일은 Git에 커밋하지 않지만 Cloud Build 제출 컨텍스트에는 포함된다.

```powershell
.\scripts\prepare_inference_runtime.ps1
```

```powershell
$ProjectId = "YOUR_PROJECT_ID"
$Region = "YOUR_REGION"
$Repository = "brainon"
$Image = "$Region-docker.pkg.dev/$ProjectId/$Repository/brainon-inference:2026-09-09"
$ResultBucket = "YOUR_PRIVATE_RESULT_BUCKET"
$ServiceAccount = "brainon-inference@$ProjectId.iam.gserviceaccount.com"

gcloud.cmd config set project $ProjectId
gcloud.cmd builds submit inference --tag $Image

gcloud.cmd run deploy brainon-inference `
  --image $Image `
  --region $Region `
  --service-account $ServiceAccount `
  --no-allow-unauthenticated `
  --gpu 1 `
  --cpu 4 `
  --memory 16Gi `
  --concurrency 1 `
  --timeout 3600 `
  --env-vars-file inference/cloud-run.env.yaml
```

Cloud Build가 비공개 `brainCDSS/model` 저장소를 읽어야 한다면 GitHub 연결 또는 Artifact Registry에 게시한 `brainon-ai` wheel을 사용하도록 빌드 인증을 먼저 구성한다.

## backend 설정

backend와 Celery 서비스에 같은 값을 넣는다.

```text
INFERENCE_API_URL=https://brainon-inference-....run.app
GCS_NIFTI_ALLOWED_BUCKETS=brainon-cdss-datasets,brainon-cdss-inference-results
INFERENCE_USE_ID_TOKEN=true
INFERENCE_AUTH_AUDIENCE=https://brainon-inference-....run.app
INFERENCE_TIMEOUT_SECONDS=600
```

backend/Celery 서비스 계정에는 Cloud Run Invoker 권한을, inference 서비스 계정에는 모델 버킷 Object Viewer와 결과 버킷 Object Creator 권한을 부여한다. 배포 후 `/ready`가 `ready: true`인지 확인하고 합성 NIfTI로 한 건을 실행한다.
