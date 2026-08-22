from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, Response
from pydantic import BaseModel, ConfigDict

from routemind_compute.api.observability import RequestObservabilityMiddleware, metrics_response


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["UP"]


class SystemInfoResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    service: Literal["compute-api"]
    runtime: Literal["python"]
    architecture_version: Literal["v1"]
    durable_state_owner: Literal[False]


app = FastAPI(title="RouteMind Compute API", version="0.1.0")
app.add_middleware(RequestObservabilityMiddleware)


@app.get("/healthz", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="UP")


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return metrics_response()


@app.get("/api/v1/system", response_model=SystemInfoResponse)
def system_info() -> SystemInfoResponse:
    return SystemInfoResponse(
        service="compute-api",
        runtime="python",
        architecture_version="v1",
        durable_state_owner=False,
    )
