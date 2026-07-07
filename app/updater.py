from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock

from app.config import AppConfig
from app.schemas import AdminStatusResponse, SyncResponse
from app.sources import SourceLoader
from app.state import SourceStateStore
from app.text_utils import chunk_text
from app.vector_store import VectorStore


class KnowledgeBaseUpdater:
    def __init__(
        self,
        config: AppConfig,
        vector_store: VectorStore,
        source_loader: SourceLoader | None = None,
        state_store: SourceStateStore | None = None,
    ) -> None:
        self.config = config
        self.vector_store = vector_store
        self.source_loader = source_loader or SourceLoader.from_config(config)
        self.state_store = state_store or SourceStateStore(config.metadata_db_path)
        self._last_sync_at: str | None = None
        self._last_sync_summary: SyncResponse | None = None
        self._lock = Lock()

    def sync(self) -> SyncResponse:
        with self._lock:
            updated_sources: list[str] = []
            skipped_sources: list[str] = []
            failed_sources: list[str] = []
            error_details: dict[str, str] = {}

            for source in self.config.sources:
                try:
                    document = self.source_loader.load(source)
                    previous_fingerprint = self.state_store.get_fingerprint(source.id)

                    if previous_fingerprint == document.fingerprint:
                        skipped_sources.append(source.id)
                        continue

                    chunks = chunk_text(
                        document.content,
                        chunk_size=self.config.chunk_size,
                        chunk_overlap=self.config.chunk_overlap,
                    )
                    self.vector_store.replace_source_chunks(source.id, chunks, document.location)
                    self.state_store.upsert_fingerprint(
                        source.id,
                        document.fingerprint,
                        datetime.now(timezone.utc).isoformat(),
                    )
                    updated_sources.append(source.id)
                except Exception as exc:
                    failed_sources.append(source.id)
                    error_details[source.id] = str(exc)

            response = SyncResponse(
                updated_sources=updated_sources,
                skipped_sources=skipped_sources,
                failed_sources=failed_sources,
                error_details=error_details,
            )
            self._last_sync_at = datetime.now(timezone.utc).isoformat()
            self._last_sync_summary = response
            return response

    def admin_status(self, metrics: dict[str, float | int]) -> AdminStatusResponse:
        return AdminStatusResponse(
            last_sync_at=self._last_sync_at,
            source_count=len(self.config.sources),
            indexed_sources=self.state_store.list_sources(),
            last_sync_summary=self._last_sync_summary,
            metrics=metrics,
        )
