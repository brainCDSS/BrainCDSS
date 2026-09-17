# REST API versioning

## Consultation messages

`GET|POST /api/v1/consultations/{consultation_id}/messages` is the durable,
participant-only collaboration message contract. GET accepts an optional
`after` message UUID cursor and returns at most 100 chronological messages.
POST accepts `{ "content": string }` with a trimmed length of 1–2000
characters and is available while the consultation is `REQUESTED`, `ACCEPTED`,
or `IN_PROGRESS`. The response schema is defined in
`consultation-messages.schema.json`.

URI major version(`/api/v1/`)을 사용한다. 같은 major 안에서는 필드 추가를 선택적으로 하고 기존 의미·타입을 바꾸지 않는다. error는 인접 schema를 따른다.
