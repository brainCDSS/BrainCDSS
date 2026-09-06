from __future__ import annotations

from collections import defaultdict
from threading import RLock


_LOCK = RLock()

_COUNTERS = defaultdict(float)

_HISTOGRAMS = {
    "ai_analysis_duration_seconds": {
        "count": 0.0,
        "sum": 0.0,
    },
}


METRIC_HELP = {
    "ai_analysis_requests_total": (
        "Total AI analysis requests observed by BrainOn."
    ),
    "ai_analysis_duration_seconds": (
        "AI analysis duration in seconds."
    ),
    "dicom_sync_failures_total": (
        "Total DICOM synchronization failures."
    ),
    "integration_requests_total": (
        "Total external integration requests."
    ),
    "radiology_reports_finalized_total": (
        "Total finalized radiology reports."
    ),
    "brainon_metrics_scrapes_total": (
        "Total successful /internal/metrics scrapes."
    ),
}


for _name in (
    "ai_analysis_requests_total",
    "dicom_sync_failures_total",
    "integration_requests_total",
    "radiology_reports_finalized_total",
    "brainon_metrics_scrapes_total",
):
    _COUNTERS[_name] = 0.0


def increment_counter(
    name: str,
    amount: float = 1.0,
):
    with _LOCK:
        _COUNTERS[name] += float(amount)


def observe_duration(
    name: str,
    seconds: float,
):
    value = float(seconds)

    if value < 0:
        return

    with _LOCK:
        item = _HISTOGRAMS.setdefault(
            name,
            {
                "count": 0.0,
                "sum": 0.0,
            },
        )
        item["count"] += 1.0
        item["sum"] += value


def _number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))

    return format(value, ".12g")


def render_prometheus() -> str:
    increment_counter(
        "brainon_metrics_scrapes_total"
    )

    lines = [
        "# HELP brainon_build_info BrainOn Django backend build information.",
        "# TYPE brainon_build_info gauge",
        'brainon_build_info{service="django-backend"} 1',
    ]

    with _LOCK:
        counters = dict(_COUNTERS)
        histograms = {
            name: dict(value)
            for name, value
            in _HISTOGRAMS.items()
        }

    for name in sorted(counters):
        help_text = METRIC_HELP.get(
            name,
            f"BrainOn counter {name}.",
        )

        lines.extend([
            f"# HELP {name} {help_text}",
            f"# TYPE {name} counter",
            f"{name} {_number(counters[name])}",
        ])

    for name in sorted(histograms):
        help_text = METRIC_HELP.get(
            name,
            f"BrainOn duration metric {name}.",
        )
        item = histograms[name]

        lines.extend([
            f"# HELP {name} {help_text}",
            f"# TYPE {name} summary",
            (
                f"{name}_count "
                f"{_number(item['count'])}"
            ),
            (
                f"{name}_sum "
                f"{_number(item['sum'])}"
            ),
        ])

    return "\n".join(lines) + "\n"
