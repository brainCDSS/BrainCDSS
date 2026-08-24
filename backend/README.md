# Backend

목적: Django/DRF modular monolith가 인증·RBAC·업무 orchestration·notification/Celery를 소유한다. 각 domain은 models/services/selectors/api/tasks 경계로 확장하며 다른 앱 model 직접 참조를 최소화한다. 추론 모델, 실제 환자자료, MCP DB 접근은 금지한다. 진입점은 manage.py/config. 설치 후 `python manage.py runserver 0.0.0.0:8080`; worker `celery -A config worker -l INFO`; beat `celery -A config beat -l INFO`. 검증은 test settings로 check/test. 환경변수는 root example 참조. 다음 작업은 승인된 domain model/API와 role/permission seed다.

