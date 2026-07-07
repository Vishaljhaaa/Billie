from __future__ import annotations

import threading

from app.updater import KnowledgeBaseUpdater


class SyncScheduler:
    def __init__(self, updater: KnowledgeBaseUpdater, interval_minutes: int) -> None:
        self.updater = updater
        self.interval_seconds = max(60, interval_minutes * 60)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.updater.sync()
            self._stop_event.wait(self.interval_seconds)
