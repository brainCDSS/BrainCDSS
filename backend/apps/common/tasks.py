"""Common Celery tasks."""

# ---------------------------------------------------------------------
# BrainOn observability probe
#
# Safe no-op task used only to verify:
# RabbitMQ -> Celery Worker -> Celery Events -> Prometheus.
# ---------------------------------------------------------------------

from celery import shared_task


@shared_task(
    name="brainon.observability.ping",
    ignore_result=True,
)
def observability_ping():
    return {
        "status": "OK",
        "service": "celery-worker",
    }
