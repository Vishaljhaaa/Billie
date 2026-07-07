from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse

from app.admin import render_admin_page, render_home_page
from app.auth import AuthManager
from app.chatbot import RetrievalChatbot
from app.config import AppConfig
from app.llm import OpenAICompatibleLLMClient
from app.monitoring import AppMonitor
from app.schemas import ChatRequest, ChatResponse, SyncResponse
from app.scheduler import SyncScheduler
from app.updater import KnowledgeBaseUpdater
from app.vector_store import VectorStore


@dataclass
class ServiceContainer:
    config: AppConfig
    vector_store: Any
    updater: KnowledgeBaseUpdater
    chatbot: RetrievalChatbot
    scheduler: SyncScheduler
    auth: AuthManager
    monitor: AppMonitor


def build_services(
    config: AppConfig,
    *,
    vector_store: Any | None = None,
    updater: KnowledgeBaseUpdater | None = None,
    chatbot: RetrievalChatbot | None = None,
    scheduler: SyncScheduler | None = None,
    auth: AuthManager | None = None,
    monitor: AppMonitor | None = None,
) -> ServiceContainer:
    monitor = monitor or AppMonitor()
    vector_store = vector_store or VectorStore(config)
    updater = updater or KnowledgeBaseUpdater(config, vector_store)
    llm_client = OpenAICompatibleLLMClient(config.llm) if config.llm.enabled else None
    chatbot = chatbot or RetrievalChatbot(config, vector_store, monitor, llm_client)
    scheduler = scheduler or SyncScheduler(updater, config.poll_interval_minutes)
    auth = auth or AuthManager(config.auth)
    return ServiceContainer(
        config=config,
        vector_store=vector_store,
        updater=updater,
        chatbot=chatbot,
        scheduler=scheduler,
        auth=auth,
        monitor=monitor,
    )


def create_app(
    config: AppConfig | None = None,
    *,
    services: ServiceContainer | None = None,
    run_scheduler: bool = True,
) -> FastAPI:
    config = config or AppConfig.load()
    services = services or build_services(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.services = services
        result = services.updater.sync()
        services.monitor.record_sync(len(result.failed_sources))
        if run_scheduler:
            services.scheduler.start()
        try:
            yield
        finally:
            if run_scheduler:
                services.scheduler.stop()

    app = FastAPI(
        title="Dynamic Knowledge Base Chatbot",
        description="Chatbot service with automatic vector database refresh.",
        lifespan=lifespan,
    )
    app.middleware("http")(services.monitor.middleware())

    def get_services(request: Request) -> ServiceContainer:
        return request.app.state.services

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return render_home_page()

    @app.get("/metrics")
    def metrics(request: Request):
        current = get_services(request)
        return current.monitor.metrics_response()

    @app.post("/sync", response_model=SyncResponse)
    def sync_now(
        request: Request,
        _: None = Depends(services.auth.require_admin_key),
    ) -> SyncResponse:
        current = get_services(request)
        result = current.updater.sync()
        current.monitor.record_sync(len(result.failed_sources))
        return result

    @app.post("/chat", response_model=ChatResponse)
    def chat(
        request: Request,
        request_body: ChatRequest,
        _: None = Depends(services.auth.require_api_key),
    ) -> ChatResponse:
        current = get_services(request)
        return current.chatbot.answer(request_body.question)

    @app.get("/admin", response_class=HTMLResponse)
    def admin_page() -> str:
        return render_admin_page()

    @app.get("/admin/status")
    def admin_status(
        request: Request,
        _: None = Depends(services.auth.require_admin_key),
    ):
        current = get_services(request)
        return current.updater.admin_status(current.monitor.snapshot())

    @app.post("/admin/sync", response_model=SyncResponse)
    def admin_sync(
        request: Request,
        _: None = Depends(services.auth.require_admin_key),
    ) -> SyncResponse:
        current = get_services(request)
        result = current.updater.sync()
        current.monitor.record_sync(len(result.failed_sources))
        return result

    return app
