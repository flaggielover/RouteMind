from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from routemind_compute.api.observability import RequestObservabilityMiddleware, metrics_response
from routemind_compute.application.registry import StrategyRegistry, default_registry
from routemind_compute.domain.dispatch import CourierCandidate, DispatchProblem, GeoPoint


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4173", "http://127.0.0.1:4173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.add_middleware(RequestObservabilityMiddleware)
REGISTRY: StrategyRegistry = default_registry()


class GeoPointRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class CourierCandidateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    courier_id: str = Field(min_length=1, max_length=128)
    location: GeoPointRequest


class DispatchSnapshotRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str = Field(min_length=1, max_length=128)
    strategy: str = Field(default="nearest", min_length=1, max_length=64)
    pickup: GeoPointRequest
    candidates: list[CourierCandidateRequest] = Field(default_factory=list, max_length=64)


class DispatchSnapshotResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: Literal["live"]
    generated_at: datetime
    request_id: str
    strategy: str
    strategy_version: str
    selected_courier: str | None
    score: float | None
    rationale: tuple[str, ...]
    latency_millis: float
    metadata: tuple[tuple[str, str], ...]
    trace_id: str


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


@app.post("/api/v1/dispatch/snapshot", response_model=DispatchSnapshotResponse)
def dispatch_snapshot(
    payload: DispatchSnapshotRequest, request: Request
) -> DispatchSnapshotResponse:
    try:
        problem = DispatchProblem(
            payload.request_id,
            GeoPoint(payload.pickup.latitude, payload.pickup.longitude),
            tuple(
                CourierCandidate(
                    candidate.courier_id,
                    GeoPoint(candidate.location.latitude, candidate.location.longitude),
                )
                for candidate in payload.candidates
            ),
        )
        decision = REGISTRY.solve(payload.strategy, problem)
    except (KeyError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return DispatchSnapshotResponse(
        source="live",
        generated_at=datetime.now(UTC),
        request_id=decision.request_id,
        strategy=decision.strategy,
        strategy_version=decision.strategy_version,
        selected_courier=decision.courier_id,
        score=decision.score,
        rationale=decision.rationale,
        latency_millis=decision.latency_millis,
        metadata=decision.metadata,
        trace_id=getattr(request.state, "trace_id", "unavailable"),
    )
