# BrainOn CDSS 저장소 작업 규칙

## 목적과 구조
이 모노레포는 의료진 웹(`frontend`), 독립 배포되는 환자·의료진 Flutter 앱(`mobile/patient-app`, `mobile/clinician-app`), Django modular monolith(`backend`), 배포용 영상 추론(`inference`), Genkit/Gemini 어시스턴트(`assistant-service`), 조회 전용 Clinical MCP(`mcp-server`)와 계약·인프라를 함께 관리한다.

## 불변 규칙
- 모델 학습 코드는 별도 `brainon-model-training` 저장소에 둔다. `ml/`, `training/`, `experiments/`, `datasets/`를 만들지 않는다.
- Redis 패키지·서비스·환경변수·channel layer를 추가하지 않는다. Celery broker는 RabbitMQ이며 상태는 필요 시 PostgreSQL 업무 테이블에 둔다.
- 실제 환자정보, DICOM/NIfTI, 모델 가중치, API key, 서비스 계정 key를 저장하거나 로그에 남기지 않는다.
- MCP는 PostgreSQL에 직접 접근하지 않고 Django 내부 API의 조회 전용 기능만 사용한다.
- Django 앱 간 직접 참조를 최소화하고 service 계층 또는 명시적 인터페이스를 사용한다.
- API 또는 RabbitMQ event schema 변경 시 `contracts/`와 contract test를 함께 수정한다.
- production dependency 추가 시 필요성, 대안, 보안·운영 영향을 PR에 문서화한다.
- 기존 사용자 코드를 임의로 삭제하거나 되돌리지 않는다. 변경 후 관련 test/lint/build를 실행한다.

## 로컬 실행
`Copy-Item .env.example .env` 후 `docker compose up --build postgres rabbitmq backend`를 실행한다. 전체 절차는 `README.md`와 서비스별 README를 따른다.

## 자주 쓰는 검증
- Backend: `python backend/manage.py check --settings=config.settings.test` 및 `python backend/manage.py test apps.common --settings=config.settings.test`
- Frontend: `npm --prefix frontend run lint && npm --prefix frontend test && npm --prefix frontend run build`
- Mobile: `cd mobile/patient-app; flutter analyze; flutter test` 및 `cd mobile/clinician-app; flutter analyze; flutter test`; 공통 package도 별도 검증한다.
- Inference: `python -m pytest inference/tests`
- Assistant: `npm --prefix assistant-service test`
- MCP: `python -m pytest mcp-server/tests`
- Contracts/safety: `python tests/contract/validate_contracts.py` 및 `python tests/security/repository_policy_test.py`

## 완료 조건
요청 범위의 코드·문서·계약이 일치하고, 관련 검증 결과가 기록되며, 실행하지 못한 검증과 이유 및 정확한 재실행 명령이 보고되어야 한다. Placeholder는 `TODO`, `NOT_IMPLEMENTED`, `MODEL_NOT_CONFIGURED`, `MOCK`으로 명시한다.
