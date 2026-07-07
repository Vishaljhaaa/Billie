from __future__ import annotations

from threading import Lock
from time import perf_counter

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, generate_latest
from starlette.responses import Response


class AppMonitor:
    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self._lock = Lock()
        self._snapshot = {
            "http_requests": 0,
            "chat_requests": 0,
            "sync_runs": 0,
            "sync_failures": 0,
            "llm_calls": 0,
            "llm_failures": 0,
        }
        self.http_requests = Counter(
            "chatbot_http_requests_total",
            "Total HTTP requests served by the chatbot service.",
            ["method", "path", "status_code"],
            registry=self.registry,
        )
        self.request_latency = Histogram(
            "chatbot_http_request_duration_seconds",
            "HTTP request latency.",
            ["method", "path"],
            registry=self.registry,
        )
        self.sync_counter = Counter(
            "chatbot_sync_runs_total",
            "Knowledge base sync runs.",
            registry=self.registry,
        )
        self.sync_failure_counter = Counter(
            "chatbot_sync_failures_total",
            "Knowledge base sync failures.",
            registry=self.registry,
        )
        self.llm_counter = Counter(
            "chatbot_llm_calls_total",
            "LLM calls made by the chatbot.",
            registry=self.registry,
        )
        self.llm_failure_counter = Counter(
            "chatbot_llm_failures_total",
            "Failed LLM calls.",
            registry=self.registry,
        )

    def middleware(self):
        async def instrument(request, call_next):
            start = perf_counter()
            response = await call_next(request)
            duration = perf_counter() - start
            path = request.url.path
            self.http_requests.labels(request.method, path, str(response.status_code)).inc()
            self.request_latency.labels(request.method, path).observe(duration)
            with self._lock:
                self._snapshot["http_requests"] += 1
            return response

        return instrument

    def record_chat(self) -> None:
        with self._lock:
            self._snapshot["chat_requests"] += 1

    def record_sync(self, failed_count: int) -> None:
        self.sync_counter.inc()
        with self._lock:
            self._snapshot["sync_runs"] += 1
            self._snapshot["sync_failures"] += failed_count
        if failed_count:
            self.sync_failure_counter.inc(failed_count)

    def record_llm_success(self) -> None:
        self.llm_counter.inc()
        with self._lock:
            self._snapshot["llm_calls"] += 1

    def record_llm_failure(self) -> None:
        self.llm_failure_counter.inc()
        with self._lock:
            self._snapshot["llm_failures"] += 1

    def snapshot(self) -> dict[str, float | int]:
        with self._lock:
            return dict(self._snapshot)

    def metrics_response(self) -> Response:
        return Response(generate_latest(self.registry), media_type=CONTENT_TYPE_LATEST)
