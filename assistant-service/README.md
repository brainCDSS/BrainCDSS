# Assistant service

목적: Genkit/Gemini 연결을 위한 TypeScript adapter, 역할별 flow, MCP client, guardrail, 관측성 경계를 제공한다. 공식 SDK API를 검증하지 못했으므로 현재 package를 추측하지 않고 deterministic MockProvider만 실행한다. RAG/vector DB와 상태변경 tool은 금지한다. 진입점 `src/api/server.ts`; `npm install && npm run dev`; test/build는 npm scripts. `GEMINI_API_KEY`가 비면 mock이다. 다음 작업은 공식 문서와 조직 승인 model 확인 후 Gemini adapter다.
