# 2026-09-08 작업 기록

## 기준과 최종 범위

- 시작 시 hy, 로컬 dev, origin/dev: `e6dd16a582f3648463313fa39997d4cc817c44fc`.
- 작업 브랜치: `feat/inference-mock-flow`. 원격 fetch, commit, push는 하지 않음.
- mock 서버는 `mocks/inference-server`에 배치.
- `inference/`의 이번 코드·테스트·README 수정은 작업 전 상태로 복구.
- Backend의 임시 MockAnalysis 모델·API·worker 작업·테스트·설정은 사용자 요청으로 제거.
- mock migration을 0002로 되돌린 뒤 파일 제거. 합성 mock 기록도 제거.
- 기존 임상 AIAnalysis와 데이터는 변경하지 않음.

## 유지한 환경 수정

- 로컬 .env의 POSTGRES_PASSWORD를 기존 정상 Backend의 값과 정렬. 비밀값은 기록하지 않음.
- common/tasks.py와 tasks/ 패키지 충돌을 정리. broker_ping과 outbox 작업 import를 tasks/__init__.py에 통합.
- RabbitMQ 4.3.5에서 발생한 transient non-exclusive 큐 거부 오류를 제어·이벤트 큐 exclusive 설정으로 해결.
- 해당 설정 지원을 위해 기존 Celery 최소 버전을 5.6.3으로 변경. 새 production 패키지 추가 없음.
- Compose override는 worker의 DJANGO_SECRET_KEY와 독립 inference-mock 서비스를 설정.

## 검증 구분

앞서 임시 Backend 구현에서는 실제 RabbitMQ/Celery/FastAPI/PostgreSQL 경로로
QUEUED → PROCESSING → COMPLETED/FAILED를 검증했다. 그러나 해당 구현은 이후
제거했으므로 이 결과를 현재 기능의 완료 증거로 사용하면 안 된다.

현재 확인 대상은 독립 mock 서버 성공·실패 계약, 기존 inference 테스트,
Django 검사·기존 common 테스트, Celery 작업 3개 등록과 broker_ping 실행이다.
기존 AIAnalysis API와 mock 서버의 비동기 연결은 후속 작업으로 남아 있다.

최종 검증 결과:
- 독립 mock 테스트 7개, 복구된 inference 테스트 2개 통과.
- Django check 및 복구 후 기존 common 테스트 1개 통과, migration 누락 없음.
- 호스트 127.0.0.1:8110에서 health/ready 200, 성공 200, 의도적 실패 500과 응답 본문 확인.
- worker 작업 3개 등록. broker_ping `2a6bd902-adfb-4ce9-b18d-8be94ee28e48` received/succeeded, 반환값 ok 확인.
- PostgreSQL, RabbitMQ, Backend, inference-api, inference-mock healthy; Celery worker ready.
- 기존 JSON 계약 검사 6개, repository safety policy, diff 공백 검사 통과.
- TestClient upstream deprecation 경고가 있으며 테스트 실패는 없음.

## 재검증 명령

```powershell
docker compose -f compose.yaml -f compose.mock.yaml exec inference-mock python -m pytest tests -q
docker compose --profile ai exec inference-api python -m pytest tests -q
docker compose exec backend python manage.py check
docker compose exec backend python manage.py test apps.common apps.ai_analysis --settings=config.settings.test
docker compose exec celery-worker celery -A config inspect registered
docker compose exec backend celery -A config call apps.common.tasks.broker_ping
docker compose logs celery-worker --tail 20
python tests/contract/validate_contracts.py
python tests/security/repository_policy_test.py
git diff --check
```
