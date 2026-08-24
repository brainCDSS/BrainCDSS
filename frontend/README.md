# Frontend

목적: 의료진 React/Vite shell과 backend API 소비 경계를 제공한다. 업무 화면은 `src/features`, 공통 UI는 `shared`, 요청은 `api/client.ts`에 둔다. 실제 임상 규칙·Gemini 직접 호출·영상 파일은 두지 않는다. 진입점은 `src/main.tsx`. `npm install && npm run dev`, 검증은 `npm run lint && npm test && npm run build`. 환경변수는 `VITE_BACKEND_URL`. 다음 작업은 인증 계약 확정 후 routing/RBAC UI를 추가하는 것이다.
