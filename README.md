# BrainOn CDSS

BrainOn CDSS는 진료 workflow, 의료영상 AI 결과, 약물 안전성, 알림과 보조 AI를 연결하기 위한 초기 개발 모노레포다. 현재 범위는 팀이 같은 경계와 계약에서 개발을 시작할 수 있는 실행 가능한 골격이며 임상 업무 규칙이나 실제 AI 모델은 구현하지 않는다.

## 기술 스택과 서비스

| 영역 | 기술 | 책임 |
|---|---|---|
| 의료진 웹 | React, Vite, TypeScript | App shell, backend API 소비, 향후 OHIF/Three.js/WebXR 연결 |
| 환자 모바일 | Flutter | 환자 self-service, 알림과 assistant 연결 지점; 독립 배포 |
| 의료진 모바일 | Flutter | 의료진 workflow와 응급 알림 연결 지점; 독립 배포 |
| Backend | Django, DRF, JWT, Celery | modular monolith, RBAC, REST, 알림, 업무 orchestration |
| 추론 | FastAPI, 향후 MOSEC | 배포용 model adapter, DICOM SEG/SR 결과 경계 |
| Assistant | TypeScript, Genkit/Gemini adapter | 역할별 flow, guardrail, MCP client; browser가 Gemini를 직접 호출하지 않음 |
| Clinical tools | Python MCP adapter | Django 내부 API만 호출하는 조회 전용 tool |
| 기반 | PostgreSQL, RabbitMQ, Orthanc/OHIF, GCS, MLflow, OpenTelemetry/Grafana stack | 저장, event, 영상, artifact, 관측성 |

모델 학습, dataset, experiment는 이 저장소 범위가 아니며 별도 `brainon-model-training` 저장소에서 관리한다.

## 저장소 구조
`frontend/`, `mobile/patient-app/`, `mobile/clinician-app/`, `backend/`, `inference/`, `assistant-service/`, `mcp-server/`는 실행 단위다. 모바일의 검증된 비임상 공통 경계는 `mobile/packages/`에 둔다. `contracts/`는 서비스 간 source of truth, `tools/`는 안전한 운영 CLI, `mocks/`는 외부 연동 대역, `infra/`는 local/template 설정, `tests/`는 횡단 검증, `docs/`는 설계·runbook을 담는다.

```mermaid
flowchart LR
  Web[React Web] --> API[Django REST/ASGI]
  PatientMobile[Patient Flutter] --> API
  ClinicianMobile[Clinician Flutter] --> API
  API --> PG[(PostgreSQL)]
  API --> MQ[(RabbitMQ)]
  MQ --> CW[Celery Worker/Beat]
  API --> INF[FastAPI inference]
  INF --> MW[MOSEC worker adapter]
  INF --> GCS[(GCS model/artifact)]
  INF -.metadata.-> MLF[MLflow]
  API --> OR[Orthanc/DICOMweb]
  Web --> OHIF[OHIF]
  OHIF --> OR
  API --> AST[Assistant service]
  AST --> GEM[Gemini external API]
  AST --> MCP[MCP server]
  MCP -->|read-only internal API| API
  API -.telemetry.-> OBS[OTel / Prometheus / Grafana / Loki / Alloy]
```

## 로컬 시작
1. `Copy-Item .env.example .env`(Linux/macOS: `cp .env.example .env`) 후 TODO 값을 로컬 전용 값으로 바꾼다.
2. 최소 환경: `docker compose up --build postgres rabbitmq backend`.
3. 선택 profile: `docker compose --profile ai --profile imaging --profile assistant up --build`.
4. 웹: `npm --prefix frontend install && npm --prefix frontend run dev`.
5. 환자 모바일: `cd mobile/patient-app && flutter pub get && flutter run`.
6. 의료진 모바일: `cd mobile/clinician-app && flutter pub get && flutter run`.

기본 health는 backend `http://localhost:8080/api/v1/health/`, inference `http://localhost:8100/health`, assistant `http://localhost:8200/health`다. 테스트 명령은 `AGENTS.md`와 각 서비스 README에 있다.

## 구현 상태
Health endpoint, API client 경계, deterministic mock, JSON Schema와 안전검사는 구현되어 있다. 임상 모델/API, JWT 발급 flow, 실제 Gemini/FCM/DUR/허가정보/GCS/MLflow/MOSEC/OHIF 연결, DICOM SEG/SR 생성, RabbitMQ→WebSocket bridge는 명시적 Placeholder다. 개발용 in-memory WebSocket channel은 단일 프로세스 전용이며 현재 dependency에 포함하지 않았다.

> 실제 환자정보, 비식별화되지 않은 영상, secret 또는 모델 가중치를 이 저장소에 저장하지 않는다.
