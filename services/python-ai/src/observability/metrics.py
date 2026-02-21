from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock


class MetricsRegistry:
    def __init__(self):
        self._lock = Lock()
        self.http_requests = defaultdict(int)
        self.http_latency_ms_sum = defaultdict(float)
        self.http_latency_ms_count = defaultdict(int)

    def record_http(self, method: str, path: str, status: int, latency_ms: float) -> None:
        key = (method, path, str(status))
        with self._lock:
            self.http_requests[key] += 1
            lk = (method, path)
            self.http_latency_ms_sum[lk] += latency_ms
            self.http_latency_ms_count[lk] += 1

    def render_prometheus(self) -> str:
        lines = [
            "# HELP traceon_http_requests_total Total HTTP requests",
            "# TYPE traceon_http_requests_total counter",
        ]
        for (method, path, status), count in sorted(self.http_requests.items()):
            lines.append(
                f'traceon_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
            )

        lines.extend(
            [
                "# HELP traceon_http_request_latency_ms_sum Sum of HTTP request latency (ms)",
                "# TYPE traceon_http_request_latency_ms_sum counter",
            ]
        )
        for (method, path), total in sorted(self.http_latency_ms_sum.items()):
            lines.append(f'traceon_http_request_latency_ms_sum{{method="{method}",path="{path}"}} {total:.3f}')

        lines.extend(
            [
                "# HELP traceon_http_request_latency_ms_count Count of HTTP request latency samples",
                "# TYPE traceon_http_request_latency_ms_count counter",
            ]
        )
        for (method, path), count in sorted(self.http_latency_ms_count.items()):
            lines.append(f'traceon_http_request_latency_ms_count{{method="{method}",path="{path}"}} {count}')

        return "\n".join(lines) + "\n"


metrics_registry = MetricsRegistry()


def monotonic_ms() -> float:
    return time.perf_counter() * 1000.0
