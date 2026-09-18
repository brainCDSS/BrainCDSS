# REST API versioning

## Imaging NIfTI viewer manifest

`GET /api/v1/imaging-studies/{study_id}/nifti-viewer` is an additive authenticated
clinical endpoint for the patient chart. It returns the study's source NIfTI inputs
and empty derived-overlay arrays. It enforces patient-care assignment scope. AI
overlays remain available only through the existing analysis manifest endpoint; the
patient chart displays its segmentation mask without probability or XAI layers.

URI major version(`/api/v1/`)을 사용한다. 같은 major 안에서는 필드 추가를 선택적으로 하고 기존 의미·타입을 바꾸지 않는다. error는 인접 schema를 따른다.

`clinical-evidence.schema.json`은 질환을 지정한 조회 응답 계약이다. 질환을
생략하면 같은 구조 3개가 상위 `items`에 반환된다.
