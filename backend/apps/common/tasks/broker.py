"""RabbitMQ와 Celery worker의 작업 전달을 확인"""

from celery import shared_task


@shared_task(
    name="common.broker_ping",
    ignore_result=True,
)
def broker_ping():
    return {
        "status": "ok",
        "service": "brainon-celery-worker",
    }