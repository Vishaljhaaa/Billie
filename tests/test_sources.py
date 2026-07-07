from __future__ import annotations

import httpx

from app.config import SourceConfig
from app.sources import SourceLoader


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


def test_source_loader_retries_url_fetch(monkeypatch):
    attempts = {"count": 0}

    def flaky_get(self, url, headers=None):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise httpx.ConnectError("temporary failure")
        return FakeResponse("<html><body><h1>Fresh docs</h1></body></html>")

    monkeypatch.setattr(httpx.Client, "get", flaky_get)
    loader = SourceLoader(timeout_seconds=1, max_retries=3, retry_backoff_seconds=0)

    document = loader.load(SourceConfig(id="docs", type="url", url="https://example.com"))

    assert attempts["count"] == 3
    assert document.source_id == "docs"
    assert "Fresh docs" in document.content
