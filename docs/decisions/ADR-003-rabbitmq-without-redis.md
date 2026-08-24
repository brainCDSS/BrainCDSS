# ADR-003: RabbitMQ without alternate cache broker
Accepted. RabbitMQ가 Celery broker다. result는 기본 비활성이며 durable 업무 상태는 PostgreSQL domain table에 둔다. Beat가 예약 작업을 담당한다.

