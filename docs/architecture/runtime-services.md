# Runtime services
기본 흐름은 client → Django → PostgreSQL/RabbitMQ다. Celery가 async/notification을 담당한다. 다중 instance realtime은 향후 RabbitMQ-to-ASGI bridge를 사용하며 in-memory channel은 단일 process 전용이다.

