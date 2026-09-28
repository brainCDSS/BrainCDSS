# Celery + RabbitMQ queue layout

The backend uses one RabbitMQ broker and separates workloads by durable queue.
Task results remain in PostgreSQL business tables; the Celery result backend is
disabled.

| Queue | Current owner | Worker command |
| --- | --- | --- |
| `brainon.inference` | AI inference orchestration | `celery -A config worker -l INFO -Q brainon.inference -n inference@%h` |
| `brainon.notifications` | Notifications | `celery -A config worker -l INFO -Q brainon.notifications -n notifications@%h` |
| `brainon.integrations` | Outbox and broker checks | `celery -A config worker -l INFO -Q brainon.integrations -n integrations@%h` |
| `brainon.default` | Unclassified future tasks | `celery -A config worker -l INFO -Q brainon.default -n default@%h` |

Run commands from the backend image with `/app` as the working directory. A
worker may consume several low-volume queues by passing a comma-separated list
to `-Q`, but inference should use its own worker because it has different
timeouts and scaling requirements.

## Adding another asynchronous feature

1. Add a durable queue name and task pattern in `config/celery_queues.py`.
2. Put the task under the owning Django app's `tasks` package and give it a
   stable explicit name when external producers depend on that name.
3. Start a worker that consumes only the new queue.
4. Add a routing test before deploying it.

Set `CELERY_QUEUE_PREFIX` differently for each environment when environments
share a RabbitMQ cluster. Explicit `CELERY_QUEUE_*` values override individual
queue names. Set `CELERY_BROKER_URL` from Secret Manager rather than committing
credentials.

Inference tasks use late acknowledgement and reject messages when a worker is
lost. The task checks the analysis state before running, so a redelivered
message does not repeat an already completed analysis.
