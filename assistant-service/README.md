# Assistant service

BrainOn의 임상 AI Assistant 오케스트레이션 서비스다.

## Runtime architecture

React / Flutter
→ Django Assistant Gateway
→ assistant-service
→ MCP Server
→ Django Internal API / DB
→ Vertex AI Gemini

브라우저와 모바일 클라이언트는 Gemini 또는 MCP를 직접 호출하지 않는다.

## Gemini provider

Production/runtime provider는 Google Cloud Vertex AI만 사용한다.

필수 환경변수:

- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_LOCATION`
- `GEMINI_MODEL`
- `GOOGLE_APPLICATION_CREDENTIALS` 또는 배포 환경의 Workload Identity / Service Account

`GEMINI_API_KEY` 기반 Gemini Developer API와 runtime Mock fallback은 사용하지 않는다.

현재 기본 모델:

- `gemini-2.5-flash`

## MCP

Assistant는 MCP Server의 read-only clinical tools를 통해 환자 임상 정보를 조회한다.

현재 MCP context source:

- `get_patient_summary`
- `get_appointments`
- `get_current_medications`
- `get_medication_safety_result`
- `get_recent_test_results`
- `get_imaging_analysis_result`
- `get_clinical_record_summary`

## Correlation

Django에서 생성된 canonical request ID를 Assistant 요청의 `request_id` / `trace_id`로 유지한다.

- `X-Request-ID`
- `X-Trace-ID`
- JSON `request_id`
- JSON `trace_id`

는 동일한 correlation ID를 사용한다.

## Development

진입점:

- `src/api/server.ts`

실행:

    npm install
    npm run dev

검증:

    npm run build
    npm test

`MockProvider`는 unit test 용도로만 사용할 수 있으며 runtime fallback으로 사용하지 않는다.
