# notifications

목적: Django 내부 알림과 Celery delivery를 소유한다. models/services/selectors/api/tasks에 승인된 기능을 둔다. 별도 알림 microservice와 Redis channel layer는 금지한다. 현재 WebSocket은 미구현 TODO다. 개발 in-memory channel layer를 도입하면 단일 프로세스 전용이다. 다중 instance에서는 RabbitMQ event consumer→독립 bridge interface→ASGI WebSocket broadcaster 구조로 확장하고 event contract를 contracts에 정의한다.

