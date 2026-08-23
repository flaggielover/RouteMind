from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routemind_compute.api.observability import RequestObservabilityMiddleware
from routemind_compute.api.routes import router
from routemind_compute.api.runtime import ComputeRuntime, create_runtime

# Compatibility alias retained for callers that inject a registry in tests.
RUNTIME: ComputeRuntime = create_runtime()
REGISTRY = RUNTIME.registry


def create_app(runtime: ComputeRuntime | None = None) -> FastAPI:
    selected_runtime = runtime or RUNTIME
    application = FastAPI(title="RouteMind Compute API", version="0.1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:4173", "http://127.0.0.1:4173"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestObservabilityMiddleware, tracing=selected_runtime.tracing)
    application.state.compute_runtime = selected_runtime
    application.include_router(router)
    return application


app = create_app()
