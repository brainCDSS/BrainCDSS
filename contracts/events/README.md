# RabbitMQ event schema

Event name과 payload를 version별로 관리한다. consumer는 알 수 없는 추가 필드를 허용하고, 삭제·재해석은 새 major event version으로 발행한다. DLQ 재처리는 멱등성을 보장해야 한다.
