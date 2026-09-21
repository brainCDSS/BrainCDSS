# REST API versioning

## MLflow Registry synchronization

The read-only MLflow Registry import contract is defined in
`mlflow-registry-sync.md`. It uses a Cloud Run ID token and does not alter the
approval or routing workflow.

## Consultation messages

`GET|POST /api/v1/consultations/{consultation_id}/messages` is the durable,
participant-only collaboration message contract. GET accepts an optional
`after` message UUID cursor and returns at most 100 chronological messages.
POST accepts `{ "content": string }` with a trimmed length of 1–2000
characters and is available while the consultation is `REQUESTED`, `ACCEPTED`,
or `IN_PROGRESS`. The response schema is defined in
`consultation-messages.schema.json`.

## Imaging NIfTI viewer manifest

`GET /api/v1/imaging-studies/{study_id}/nifti-viewer` is an additive authenticated
clinical endpoint for the patient chart. It returns the study's source NIfTI inputs
and empty derived-overlay arrays. It enforces patient-care assignment scope. AI
overlays remain available only through the existing analysis manifest endpoint; the
patient chart displays its segmentation mask without probability or XAI layers.

## ML 관리

시스템 관리자의 모델 버전 승인, 종료, AI 라우팅 전환 계약은
`ml-management.md`에 정의한다. 이 API는 MLflow Tracking Server를 직접 호출하지
않으며, 이미 등록된 모델 버전과 라우팅 설정만 관리한다.

URI major version(`/api/v1/`)을 사용한다. 같은 major 안에서는 필드 추가를 선택적으로 하고 기존 의미·타입을 바꾸지 않는다. error는 인접 schema를 따른다.

`clinical-evidence.schema.json`은 질환을 지정한 조회 응답 계약이다. 질환을
생략하면 같은 구조 3개가 상위 `items`에 반환된다.
