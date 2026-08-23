from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from routemind_compute.api.observability import RequestObservabilityMiddleware, metrics_response
from routemind_compute.application.execution import execution_provenance
from routemind_compute.application.parameters import Metadata
from routemind_compute.application.registry import StrategyRegistry, default_registry
from routemind_compute.application.routebench import BenchmarkManifest, RouteBenchRunner
from routemind_compute.application.shadow import (
    RegressionGate,
    RegressionPolicy,
    ShadowManifest,
    ShadowModeEvaluator,
)
from routemind_compute.application.simulation import CourierState, DemandEvent, ScenarioManifest
from routemind_compute.application.travel import (
    DeterministicLocalTravelProvider,
    FallbackTravelTimeProvider,
)
from routemind_compute.application.twin_control import (
    TwinAction,
    TwinCommandConflict,
    TwinControlCommand,
    TwinControlEvent,
    TwinControlService,
    TwinControlState,
)
from routemind_compute.application.what_if import WhatIfRunner, WhatIfVariant
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
TWIN_CONTROL = TwinControlService(REGISTRY, TRAVEL_PROVIDER)
WHAT_IF_RUNNER = WhatIfRunner(REGISTRY, TRAVEL_PROVIDER)


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
    contract_version: Literal["v1"]
    generated_at: datetime
    request_id: str
    strategy: str
    strategy_version: str
    input_digest: str
    output_digest: str
    selected_courier: str | None
    score: float | None
    rationale: tuple[str, ...]
    latency_millis: float
    metadata: tuple[tuple[str, str], ...]
    fallback_used: bool
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


class ParameterDefinitionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    type: Literal["float"]
    default: str
    minimum: float | None
    maximum: float | None


class StrategyParameterSchemaResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy: str
    version: str
    parameters: tuple[ParameterDefinitionResponse, ...]


class ExperimentDemandRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str = Field(min_length=1, max_length=128)
    pickup: GeoPointRequest
    tick: int = Field(ge=0, le=100_000)
    zone: str = Field(default="", max_length=64)
    merchant_id: str = Field(default="", max_length=128)
    order_profile: str = Field(default="standard", min_length=1, max_length=64)


class ExperimentCourierRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    courier_id: str = Field(min_length=1, max_length=128)
    location: GeoPointRequest
    available_tick: int = Field(default=0, ge=0, le=100_000)


class RouteBenchExperimentRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    manifest_id: str = Field(min_length=1, max_length=128)
    code_version: str = Field(min_length=1, max_length=128)
    scenario_id: str = Field(min_length=1, max_length=128)
    seed: int = Field(ge=0, le=2_147_483_647)
    load_profile: str = Field(min_length=1, max_length=128)
    city_state: str = Field(min_length=1, max_length=128)
    dataset_provenance: str = Field(min_length=1, max_length=256)
    strategies: tuple[str, ...] = Field(min_length=1, max_length=6)
    configuration: tuple[tuple[str, str], ...] = Field(default=(), max_length=16)
    parameter_configuration: tuple[tuple[str, str], ...] = Field(default=(), max_length=16)
    demands: tuple[ExperimentDemandRequest, ...] = Field(min_length=1, max_length=64)
    couriers: tuple[ExperimentCourierRequest, ...] = Field(min_length=1, max_length=64)
    delay_ticks: tuple[int, ...] = Field(default=(0,), min_length=1, max_length=16)
    traffic_multiplier: float = Field(default=1.0, gt=0, le=10)


class ExperimentMetricResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy: str
    strategy_version: str
    request_count: int
    assigned_count: int
    assignment_rate: float
    runtime_millis: float
    replay_digest: str


class ExperimentResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: Literal["experiment"]
    manifest_digest: str
    output_digest: str
    metrics: tuple[ExperimentMetricResponse, ...]
    scenario_id: str
    seed: int
    configuration: tuple[tuple[str, str], ...]
    parameter_configuration: tuple[tuple[str, str], ...]
    trace_id: str


class WhatIfVariantRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    variant_id: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)
    demand_multiplier: float = Field(default=1.0, ge=0.5, le=2.0)
    supply_delta: int = Field(default=0, ge=-32, le=32)
    preparation_delay_ticks: int = Field(default=0, ge=0, le=60)
    traffic_multiplier: float = Field(default=1.0, ge=0.5, le=3.0)
    strategy: str = Field(default="nearest", min_length=1, max_length=64)
    risk_multiplier: float = Field(default=1.0, ge=0.1, le=5.0)


class WhatIfExperimentRequest(RouteBenchExperimentRequest):
    model_config = ConfigDict(frozen=True)

    recorded_run_id: str = Field(min_length=1, max_length=128)
    baseline_strategy: str = Field(default="nearest", min_length=1, max_length=64)
    variants: tuple[WhatIfVariantRequest, ...] = Field(min_length=1, max_length=4)


class WhatIfMetricResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    variant_id: str
    label: str
    strategy: str
    strategy_version: str
    request_count: int
    assigned_count: int
    assignment_rate: float
    simulated_end_tick: int
    simulated_duration_seconds: float
    risk_index: float
    replay_digest: str
    manifest_digest: str
    output_digest: str
    observed_runtime_millis: float


class WhatIfExperimentResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: Literal["what-if"]
    claim_label: Literal["scenario comparison; not a causal production claim"]
    recorded_run_id: str
    comparison_digest: str
    scenario_id: str
    seed: int
    results: tuple[WhatIfMetricResponse, ...]
    trace_id: str


class RegressionPolicyRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    minimum_samples: int = Field(default=1, ge=1, le=100_000)
    maximum_failure_rate: float = Field(default=0.0, ge=0, le=1)
    maximum_assignment_rate_drop: float = Field(default=0.0, ge=0, le=1)
    maximum_disagreement_rate: float = Field(default=1.0, ge=0, le=1)


class ShadowEvaluateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    manifest_id: str = Field(min_length=1, max_length=128)
    code_version: str = Field(min_length=1, max_length=128)
    scenario_id: str = Field(min_length=1, max_length=128)
    seed: int = Field(ge=0, le=2_147_483_647)
    active_strategy: str = Field(min_length=1, max_length=64)
    candidate_strategy: str = Field(min_length=1, max_length=64)
    policy: RegressionPolicyRequest = RegressionPolicyRequest()
    configuration: tuple[tuple[str, str], ...] = Field(default=(), max_length=32)
    problems: tuple[DispatchSnapshotRequest, ...] = Field(min_length=1, max_length=64)


class ShadowMetricsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    sample_count: int
    active_assignment_rate: float
    candidate_assignment_rate: float
    candidate_failure_rate: float
    disagreement_rate: float
    assignment_rate_drop: float


class ShadowObservationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    active_courier_id: str | None
    candidate_courier_id: str | None
    candidate_error: str | None
    disagrees: bool


class ShadowEvaluateResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: Literal["shadow"]
    action: Literal["promote", "hold"]
    reasons: tuple[str, ...]
    active_strategy: str
    candidate_strategy: str
    metrics: ShadowMetricsResponse
    observations: tuple[ShadowObservationResponse, ...]
    manifest_digest: str
    run_digest: str
    trace_id: str
    candidate_authority: Literal["none"]


class TwinControlRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    command_id: str = Field(min_length=1, max_length=128)
    action: TwinAction
    seconds: float | None = Field(default=None, ge=1, le=3600)
    speed: float | None = Field(default=None, ge=0.1, le=10)
    scenario_id: str | None = Field(default=None, min_length=1, max_length=128)
    seed: int | None = Field(default=None, ge=0, le=2_147_483_647)
    strategy: str | None = Field(default=None, min_length=1, max_length=64)


class TwinStateResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: Literal["simulation"]
    scenario_id: str
    seed: int
    strategy: str
    strategy_version: str
    status: Literal["paused", "running", "completed"]
    speed: float
    simulated_time_seconds: float
    tick: int
    generation: int
    event_count: int
    last_command_id: str | None
    replay_digest: str
    trace_id: str


class TwinEventResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    event_type: str
    simulated_time_seconds: float
    command_id: str
    details: tuple[tuple[str, str], ...]


class TwinControlResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: Literal["simulation"]
    command_id: str
    replayed: bool
    state: TwinStateResponse
    events: tuple[TwinEventResponse, ...]
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


def _twin_state_response(state: TwinControlState, trace_id: str) -> TwinStateResponse:
    return TwinStateResponse(
        source="simulation",
        scenario_id=state.scenario_id,
        seed=state.seed,
        strategy=state.strategy,
        strategy_version=state.strategy_version,
        status=state.status,
        speed=state.speed,
        simulated_time_seconds=state.simulated_time_seconds,
        tick=state.tick,
        generation=state.generation,
        event_count=state.event_count,
        last_command_id=state.last_command_id,
        replay_digest=state.replay_digest,
        trace_id=trace_id,
    )


def _twin_event_response(event: TwinControlEvent) -> TwinEventResponse:
    return TwinEventResponse(
        event_id=event.event_id,
        event_type=event.event_type,
        simulated_time_seconds=event.simulated_time_seconds,
        command_id=event.command_id,
        details=event.details,
    )


@app.get("/api/v1/twin/state", response_model=TwinStateResponse)
def twin_state(request: Request) -> TwinStateResponse:
    trace_id = getattr(request.state, "trace_id", "unavailable")
    return _twin_state_response(TWIN_CONTROL.snapshot().state, trace_id)


@app.post("/api/v1/twin/control", response_model=TwinControlResponse)
def twin_control(payload: TwinControlRequest, request: Request) -> TwinControlResponse:
    trace_id = getattr(request.state, "trace_id", "unavailable")
    try:
        command = TwinControlCommand(
            command_id=payload.command_id,
            action=payload.action,
            seconds=payload.seconds,
            speed=payload.speed,
            scenario_id=payload.scenario_id,
            seed=payload.seed,
            strategy=payload.strategy,
        )
        result = TWIN_CONTROL.apply(command)
    except TwinCommandConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except KeyError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return TwinControlResponse(
        source="simulation",
        command_id=result.command_id or payload.command_id,
        replayed=result.replayed,
        state=_twin_state_response(result.state, trace_id),
        events=tuple(_twin_event_response(event) for event in result.events),
        trace_id=trace_id,
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


@app.get(
    "/api/v1/strategies/{strategy_name}/parameters",
    response_model=StrategyParameterSchemaResponse,
)
def strategy_parameters(strategy_name: str) -> StrategyParameterSchemaResponse:
    try:
        schema = REGISTRY.parameter_schema(strategy_name)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return StrategyParameterSchemaResponse(
        strategy=schema.strategy,
        version=schema.version,
        parameters=tuple(
            ParameterDefinitionResponse(
                key=item.key,
                type=item.value_type,
                default=item.default,
                minimum=item.minimum,
                maximum=item.maximum,
            )
            for item in schema.parameters
        ),
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


@app.post("/api/v1/experiments/routebench", response_model=ExperimentResponse)
def run_routebench_experiment(
    payload: RouteBenchExperimentRequest, request: Request
) -> ExperimentResponse:
    trace_id = getattr(request.state, "trace_id", "unavailable")
    try:
        configuration: Metadata = tuple(sorted(payload.configuration))
        manifest = BenchmarkManifest(
            payload.manifest_id,
            payload.code_version,
            payload.scenario_id,
            payload.seed,
            payload.load_profile,
            payload.city_state,
            payload.dataset_provenance,
            payload.strategies,
            configuration=configuration,
            parameter_configuration=tuple(sorted(payload.parameter_configuration)),
        )
        scenario = ScenarioManifest(
            payload.scenario_id,
            payload.seed,
            tuple(
                DemandEvent(
                    demand.request_id,
                    GeoPoint(demand.pickup.latitude, demand.pickup.longitude),
                    demand.tick,
                    demand.zone,
                    demand.merchant_id,
                    demand.order_profile,
                )
                for demand in payload.demands
            ),
            tuple(
                CourierState(
                    courier.courier_id,
                    GeoPoint(courier.location.latitude, courier.location.longitude),
                    courier.available_tick,
                )
                for courier in payload.couriers
            ),
            payload.delay_ticks,
            payload.traffic_multiplier,
        )
        run = RouteBenchRunner(REGISTRY, TRAVEL_PROVIDER).run(manifest, scenario)
    except KeyError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return ExperimentResponse(
        source="experiment",
        manifest_digest=run.manifest.digest,
        output_digest=run.output_digest,
        metrics=tuple(
            ExperimentMetricResponse(
                strategy=result.strategy,
                strategy_version=result.strategy_version,
                request_count=result.request_count,
                assigned_count=result.assigned_count,
                assignment_rate=result.assignment_rate,
                runtime_millis=result.runtime_millis,
                replay_digest=result.replay_digest,
            )
            for result in run.results
        ),
        scenario_id=payload.scenario_id,
        seed=payload.seed,
        configuration=configuration,
        parameter_configuration=tuple(sorted(payload.parameter_configuration)),
        trace_id=trace_id,
    )


@app.post("/api/v1/experiments/what-if", response_model=WhatIfExperimentResponse)
def run_what_if_experiment(
    payload: WhatIfExperimentRequest, request: Request
) -> WhatIfExperimentResponse:
    trace_id = getattr(request.state, "trace_id", "unavailable")
    try:
        manifest = ScenarioManifest(
            payload.scenario_id,
            payload.seed,
            tuple(
                DemandEvent(
                    demand.request_id,
                    GeoPoint(demand.pickup.latitude, demand.pickup.longitude),
                    demand.tick,
                    demand.zone,
                    demand.merchant_id,
                    demand.order_profile,
                )
                for demand in payload.demands
            ),
            tuple(
                CourierState(
                    courier.courier_id,
                    GeoPoint(courier.location.latitude, courier.location.longitude),
                    courier.available_tick,
                )
                for courier in payload.couriers
            ),
            payload.delay_ticks,
            payload.traffic_multiplier,
        )
        variants = tuple(
            WhatIfVariant(
                variant.variant_id,
                variant.label,
                variant.demand_multiplier,
                variant.supply_delta,
                variant.preparation_delay_ticks,
                variant.traffic_multiplier,
                variant.strategy,
                variant.risk_multiplier,
            )
            for variant in payload.variants
        )
        comparison = WHAT_IF_RUNNER.run(
            payload.recorded_run_id,
            payload.baseline_strategy,
            manifest,
            variants,
        )
    except KeyError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return WhatIfExperimentResponse(
        source="what-if",
        claim_label="scenario comparison; not a causal production claim",
        recorded_run_id=comparison.recorded_run_id,
        comparison_digest=comparison.comparison_digest,
        scenario_id=comparison.scenario_id,
        seed=comparison.seed,
        results=tuple(
            WhatIfMetricResponse(
                variant_id=result.variant_id,
                label=result.label,
                strategy=result.strategy,
                strategy_version=result.strategy_version,
                request_count=result.request_count,
                assigned_count=result.assigned_count,
                assignment_rate=result.assignment_rate,
                simulated_end_tick=result.simulated_end_tick,
                simulated_duration_seconds=result.simulated_duration_seconds,
                risk_index=result.risk_index,
                replay_digest=result.replay_digest,
                manifest_digest=result.manifest_digest,
                output_digest=result.output_digest,
                observed_runtime_millis=result.observed_runtime_millis,
            )
            for result in comparison.results
        ),
        trace_id=trace_id,
    )


@app.post("/api/v1/shadow/evaluate", response_model=ShadowEvaluateResponse)
def evaluate_shadow(payload: ShadowEvaluateRequest, request: Request) -> ShadowEvaluateResponse:
    trace_id = getattr(request.state, "trace_id", "unavailable")
    try:
        policy = RegressionPolicy(
            payload.policy.minimum_samples,
            payload.policy.maximum_failure_rate,
            payload.policy.maximum_assignment_rate_drop,
            payload.policy.maximum_disagreement_rate,
        )
        manifest = ShadowManifest(
            payload.manifest_id,
            payload.code_version,
            payload.scenario_id,
            payload.seed,
            payload.active_strategy,
            payload.candidate_strategy,
            policy,
            tuple(sorted(payload.configuration)),
        )
        problems = tuple(_dispatch_problem(problem) for problem in payload.problems)
        run = ShadowModeEvaluator(REGISTRY).run(manifest, problems)
        assessment = RegressionGate().assess(run)
    except KeyError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (TimeoutError, RuntimeError, TypeError) as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "shadow_evaluation_unavailable",
                "message": "active or candidate strategy execution failed",
                "trace_id": trace_id,
                "metadata": {"failure_type": type(error).__name__},
            },
        ) from error
    return ShadowEvaluateResponse(
        source="shadow",
        action=assessment.action,
        reasons=assessment.reasons,
        active_strategy=manifest.active_strategy,
        candidate_strategy=manifest.candidate_strategy,
        metrics=ShadowMetricsResponse(
            sample_count=run.metrics.sample_count,
            active_assignment_rate=run.metrics.active_assignment_rate,
            candidate_assignment_rate=run.metrics.candidate_assignment_rate,
            candidate_failure_rate=run.metrics.candidate_failure_rate,
            disagreement_rate=run.metrics.disagreement_rate,
            assignment_rate_drop=run.metrics.assignment_rate_drop,
        ),
        observations=tuple(
            ShadowObservationResponse(
                request_id=item.request_id,
                active_courier_id=item.authoritative.courier_id,
                candidate_courier_id=item.candidate.courier_id if item.candidate else None,
                candidate_error=item.candidate_error,
                disagrees=item.disagrees,
            )
            for item in run.observations
        ),
        manifest_digest=assessment.manifest_digest,
        run_digest=assessment.run_digest,
        trace_id=trace_id,
        candidate_authority="none",
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
    canonical_input = payload.model_dump(mode="json")
    provenance = execution_provenance(canonical_input, decision)
    fallback_used = bool(selected_travel and selected_travel.fallback_used)
    if selected_travel is not None:
        metadata = (*metadata, ("selected_travel_seconds", f"{selected_travel.seconds:.3f}"))
    return DispatchSnapshotResponse(
        source="live",
        contract_version="v1",
        generated_at=datetime.now(UTC),
        request_id=decision.request_id,
        strategy=decision.strategy,
        strategy_version=decision.strategy_version,
        input_digest=provenance.input_digest,
        output_digest=provenance.output_digest,
        selected_courier=decision.courier_id,
        score=decision.score,
        rationale=decision.rationale,
        latency_millis=decision.latency_millis,
        metadata=metadata,
        fallback_used=fallback_used,
        trace_id=trace_id,
    )
