# Frontend rules

Backend 호출은 `src/api/client.ts`를 통한다. Browser에서 Gemini, DUR, 내부 DB를 직접 호출하지 않는다. 임상 화면은 승인된 contract 없이 추측해 만들지 않는다. 변경 후 lint/test/build를 실행한다.
