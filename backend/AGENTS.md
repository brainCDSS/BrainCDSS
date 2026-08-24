# Backend rules

Modular monolith 앱 간 접근은 service/interface를 우선한다. migration과 contracts를 함께 검토한다. Celery broker는 RabbitMQ이고 result backend는 기본 비활성이다. 알림은 notifications 앱과 worker가 담당한다. Redis와 실제 임상 payload를 추가하지 않는다.

