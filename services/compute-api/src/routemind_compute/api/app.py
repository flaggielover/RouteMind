from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from routemind_compute.api.observability import RequestObservabilityMiddleware, metrics_response
from routemind_compute.application.execution import execution_provenance
from routemind_compute.application.registry import StrategyRegistry, default_registry
from routemind_compute.application.travel import (
    DeterministicLocalTravelProvider,
    FallbackTravelTimeProvider,
)
from routemind_compute.domain.dispatch import (
    CourierCandidate,
    DispatchProblem,
    GeoPoint,
    TimeWindow,
)


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
TRAVEL_PROVIDER = FallbackTravelTimeProvider(
    DeterministicLocalTravelProvider(), DeterministicLocalTravelProvider()
)


class GeoPointRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class CourierCandidateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    courier_id: str = Field(min_length=1, max_length=128)
    location: GeoPointRequest
    capacity_units: float = Field(default=1.0, ge=0)
    current_load_units: float = Field(default=0.0, ge=0)
    available_from_seconds: float = Field(default=0.0, ge=0)
    available_until_seconds: float | None = Field(default=None, ge=0)
    state: Literal["available", "on_route", "offline", "paused"] = "available"
    service_risk: float = Field(default=0.0, ge=0, le=1)
    overtime_risk: float = Field(default=0.0, ge=0, le=1)
    estimated_travel_seconds: float = Field(default=0.0, ge=0)


class TimeWindowRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)


class DispatchSnapshotRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str = Field(min_length=1, max_length=128)
    strategy: str = Field(default="nearest", min_length=1, max_length=64)
    pickup: GeoPointRequest
    candidates: list[CourierCandidateRequest] = Field(default_factory=list, max_length=64)
    demand_units: float = Field(default=1.0, gt=0)
    pickup_ready_at_seconds: float = Field(default=0.0, ge=0)
    service_seconds: float = Field(default=0.0, ge=0)
    delivery_window: TimeWindowRequest | None = None
    max_service_risk: float = Field(default=1.0, ge=0, le=1)


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


class StrategyExecutionRequest(DispatchSnapshotRequest):
    scenario_id: str = Field(min_length=1, max_length=128)
    seed: int = Field(ge=0, le=2_147_483_647)
    configuration: tuple[tuple[str, str], ...] = Field(default=(), max_length=32)


class StrategyDescriptorResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    version: str
    capabilities: tuple[str, ...]
    status: Literal["available"]


class StrategyExecutionMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate_count: int
    eligible_candidate_count: int
    assigned: bool
    latency_millis: float


class StrategyExecutionProvenanceResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    scenario_id: str
    seed: int
    configuration: tuple[tuple[str, str], ...]
    input_digest: str
    output_digest: str


class StrategyExecutionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: Literal["experiment"]
    request_id: str
    strategy: str
    strategy_version: str
    selected_courier: str | None
    score: float | None
    rationale: tuple[str, ...]
    metadata: tuple[tuple[str, str], ...]
    metrics: StrategyExecutionMetrics
    provenance: StrategyExecutionProvenanceResponse
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


@app.get("/api/v1/strategies", response_model=tuple[StrategyDescriptorResponse, ...])
def strategy_catalog() -> tuple[StrategyDescriptorResponse, ...]:
    return tuple(
        StrategyDescriptorResponse(
            name=descriptor.name,
            version=descriptor.version,
            capabilities=descriptor.capabilities,
            status="available",
        )
        for descriptor in REGISTRY.descriptors()
    )


def _dispatch_problem(payload: DispatchSnapshotRequest) -> DispatchProblem:
    return DispatchProblem(
        payload.request_id,
        GeoPoint(payload.pickup.latitude, payload.pickup.longitude),
        tuple(
            CourierCandidate(
                candidate.courier_id,
                GeoPoint(candidate.location.latitude, candidate.location.longitude),
                capacity_units=candidate.capacity_units,
                current_load_units=candidate.current_load_units,
                available_from_seconds=candidate.available_from_seconds,
                available_until_seconds=candidate.available_until_seconds,
                state=candidate.state,
                service_risk=candidate.service_risk,
                overtime_risk=candidate.overtime_risk,
                estimated_travel_seconds=candidate.estimated_travel_seconds,
            )
            for candidate in payload.candidates
        ),
        demand_units=payload.demand_units,
        pickup_ready_at_seconds=payload.pickup_ready_at_seconds,
        service_seconds=payload.service_seconds,
        delivery_window=(
            TimeWindow(payload.delivery_window.start_seconds, payload.delivery_window.end_seconds)
            if payload.delivery_window is not None
            else None
        ),
        max_service_risk=payload.max_service_risk,
    )


@app.post("/api/v1/strategies/execute", response_model=StrategyExecutionResponse)
def execute_strategy(
    payload: StrategyExecutionRequest, request: Request
) -> StrategyExecutionResponse:
    trace_id = getattr(request.state, "trace_id", "unavailable")
    try:
        problem = _dispatch_problem(payload)
        decision = REGISTRY.solve(payload.strategy, problem)
    except KeyError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except (TimeoutError, RuntimeError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "strategy_unavailable",
                "message": "requested strategy execution failed",
                "trace_id": trace_id,
                "metadata": {
                    "requested_strategy": payload.strategy,
                    "fallback_strategy": "nearest",
                    "fallback_available": str("nearest" in REGISTRY.names()).lower(),
                    "failure_type": type(error).__name__,
                },
            },
        ) from error
    canonical_input = payload.model_dump(mode="json")
    canonical_input["configuration"] = sorted(payload.configuration)
    provenance = execution_provenance(canonical_input, decision)
    return StrategyExecutionResponse(
        source="experiment",
        request_id=decision.request_id,
        strategy=decision.strategy,
        strategy_version=decision.strategy_version,
        selected_courier=decision.courier_id,
        score=decision.score,
        rationale=decision.rationale,
        metadata=decision.metadata,
        metrics=StrategyExecutionMetrics(
            candidate_count=len(problem.candidates),
            eligible_candidate_count=len(problem.eligible_candidates()),
            assigned=decision.courier_id is not None,
            latency_millis=decision.latency_millis,
        ),
        provenance=StrategyExecutionProvenanceResponse(
            scenario_id=payload.scenario_id,
            seed=payload.seed,
            configuration=tuple(sorted(payload.configuration)),
            input_digest=provenance.input_digest,
            output_digest=provenance.output_digest,
        ),
        trace_id=trace_id,
    )


@app.post("/api/v1/dispatch/snapshot", response_model=DispatchSnapshotResponse)
def dispatch_snapshot(
    payload: DispatchSnapshotRequest, request: Request
) -> DispatchSnapshotResponse:
    trace_id = getattr(request.state, "trace_id", "unavailable")
    try:
        problem = _dispatch_problem(payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    try:
        decision = REGISTRY.solve(payload.strategy, problem)
    except KeyError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except (TimeoutError, RuntimeError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "strategy_unavailable",
                "message": "dispatch strategy failed",
                "trace_id": trace_id,
                "metadata": {
                    "fallback_strategy": "nearest",
                    "fallback_available": "true",
                    "failure_type": type(error).__name__,
                },
            },
        ) from error
    try:
        selected_travel = next(
            (
                TRAVEL_PROVIDER.estimate(candidate.location, problem.pickup)
                for candidate in problem.candidates
                if candidate.courier_id == decision.courier_id
            ),
            None,
        )
    except (TimeoutError, RuntimeError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "travel_provider_unavailable",
                "message": "travel metadata unavailable",
                "trace_id": trace_id,
                "metadata": {
                    "fallback_provider": "deterministic-local",
                    "fallback_available": "true",
                    "failure_type": type(error).__name__,
                },
            },
        ) from error
    metadata = (
        *decision.metadata,
        ("travel_provider", selected_travel.provider if selected_travel else "not_required"),
        ("travel_candidate_count", str(len(problem.candidates))),
        (
            "travel_fallback_used",
            str(selected_travel.fallback_used if selected_travel else False).lower(),
        ),
    )
    if selected_travel is not None:
        metadata = (*metadata, ("selected_travel_seconds", f"{selected_travel.seconds:.3f}"))
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
        metadata=metadata,
        trace_id=trace_id,
    )
