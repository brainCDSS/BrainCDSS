# Inference mock 서버

실제 모델 없이 성공·실패 HTTP 응답을 제공하는 독립 FastAPI 서버다.
Backend의 분석 생성·Celery 연동·DB 저장은 현재 연결되어 있지 않다.
요청자가 제공한 analysis_id를 응답에 반영하며, 서버가 분석 ID를 생성하지 않는다.
실제 모델·영상·개인정보·정확도 시뮬레이션은 사용하지 않는다.

## 실행

저장소 루트에서 실행한다.

```powershell
docker compose -f compose.yaml -f compose.mock.yaml up -d --build inference-mock
docker compose -f compose.yaml -f compose.mock.yaml exec inference-mock python -m pytest tests -q
```

- 호스트 주소: `http://127.0.0.1:8110`
- Compose 네트워크 내부 주소: `http://inference-mock:8100`
- 실제 inference-api는 기존 `http://localhost:8100`을 사용한다.
- `/health`: 프로세스 응답 확인.
- `/ready`: mock 활성화 확인. 모델 준비 완료를 의미하지 않는다.
- `POST /mock/inference`: 아래 요청의 outcome을 success/failure로 지정.

```powershell
$mockBody = '{"analysis_id":"00000000-0000-0000-0000-000000000001","outcome":"success"}'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8110/mock/inference -ContentType application/json -Body $mockBody
```

`INFERENCE_MOCK_ENABLED`는 기본 false이고 Compose override에서 true로 설정한다.
지연 응답은 TODO다. 기존 `response.json`은 이전 scaffold 예제로 보존하며
서버가 해당 파일을 로드하지는 않는다. 실행 계약은
[inference-mock.md](../../contracts/rest-api/inference-mock.md), 오늘 작업 기록은
[WORK_LOG.md](WORK_LOG.md)를 참고한다.
