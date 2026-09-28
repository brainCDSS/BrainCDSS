"""Gunicorn hooks for Prometheus multiprocess metrics."""

from __future__ import annotations

import os
import shutil

from prometheus_client import (
    multiprocess,
)


def on_starting(server):
    path = os.environ.get(
        "PROMETHEUS_MULTIPROC_DIR",
        "",
    )

    if not path:
        return

    shutil.rmtree(
        path,
        ignore_errors=True,
    )

    os.makedirs(
        path,
        exist_ok=True,
    )


def child_exit(
    server,
    worker,
):
    if os.environ.get(
        "PROMETHEUS_MULTIPROC_DIR"
    ):
        multiprocess.mark_process_dead(
            worker.pid
        )
