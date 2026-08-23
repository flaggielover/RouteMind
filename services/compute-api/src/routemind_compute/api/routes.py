from __future__ import annotations

import sys
from datetime import UTC, datetime
from typing import cast

from fastapi import APIRouter, HTTPException, Request, Response

from routemind_compute.api.observability import metrics_response
from routemind_compute.api.runtime import ComputeRuntime
from routemind_compute.api.schemas import (
    DispatchSnapshotRequest,
    DispatchSnapshotResponse,
    ExperimentMetricResponse,
    ExperimentResponse,
    HealthResponse,
    HotspotCellResponse,
    IntegritySignalResponse,
    LocationIntegrityBatchResponse,
    LocationIntegrityRequest,
    LocationIntegrityResponse,
    ParameterDefinitionResponse,
    RouteBenchExperimentRequest,
    SemanticMetricDefinitionResponse,
    ShadowEvaluateRequest,
    ShadowEvaluateResponse,
    ShadowMetricsResponse,
    ShadowObservationResponse,
    StrategyDescriptorResponse,
    StrategyExecutionMetrics,
    StrategyExecutionProvenanceResponse,
    StrategyExecutionRequest,
    StrategyExecutionResponse,
    StrategyParameterSchemaResponse,
    SystemInfoResponse,
    TwinControlRequest,
    TwinControlResponse,
    TwinEventResponse,
    TwinStateResponse,
    WhatIfExperimentRequest,
    WhatIfExperimentResponse,
    WhatIfMetricResponse,
)
from routemind_compute.application.execution import execution_provenance
from routemind_compute.application.location_integrity import (
    LocationObservation,
    assess_location,
    build_hotspots,
)
from routemind_compute.application.parameters import Metadata
from routemind_compute.application.registry import StrategyRegistry
from routemind_compute.application.routebench import BenchmarkManifest, RouteBenchRunner
from routemind_compute.application.semantic_metrics import MetricConsumer, metric_catalog
from routemind_compute.application.shadow import (
    RegressionGate,
    RegressionPolicy,
    ShadowManifest,
    ShadowModeEvaluator,
)
from routemind_compute.application.simulation import CourierState, DemandEvent, ScenarioManifest
from routemind_compute.application.twin_control import (
    TwinCommandConflict,
    TwinControlCommand,
    TwinControlEvent,
    TwinControlState,
)
from routemind_compute.application.verification import SolverOutputInvalidError
from routemind_compute.application.what_if import WhatIfVariant
from routemind_compute.domain.dispatch import (
    CourierCandidate,
    DispatchProblem,
    GeoPoint,
    TimeWindow,
)

router = APIRouter()


def _runtime(request: Request) -> ComputeRuntime:
    return cast(ComputeRuntime, request.app.state.compute_runtime)


def _registry(request: Request) -> StrategyRegistry:
    # Keep the historical app.REGISTRY patch point while routes use app state.
    composition = sys.modules.get("routemind_compute.api.app")
    return getattr(composition, "REGISTRY", _runtime(request).registry)


@router.get("/healthz", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="UP")


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return metrics_response()


@router.get("/api/v1/system", response_model=SystemInfoResponse)
def system_info() -> SystemInfoResponse:
    return SystemInfoResponse(
        service="compute-api",
        runtime="python",
        architecture_version="v1",
        durable_state_owner=False,
    )


@router.get(
    "/api/v1/analytics/metrics/catalog",
    response_model=tuple[SemanticMetricDefinitionResponse, ...],
)
def semantic_metric_catalog(
    consumer: MetricConsumer | None = None,
) -> tuple[SemanticMetricDefinitionResponse, ...]:
    return tuple(
        SemanticMetricDefinitionResponse(**definition.contract())
        for definition in metric_catalog(consumer)
    )


@router.post(
    "/api/v1/locations/integrity",
    response_model=LocationIntegrityBatchResponse,
)
def location_integrity(
    payload: LocationIntegrityRequest, request: Request
) -> LocationIntegrityBatchResponse:
    trace_id = getattr(request.state, "trace_id", "unavailable")
    try:
        observations = tuple(
            LocationObservation(
                courier_id=item.courier_id,
                location=GeoPoint(item.location.latitude, item.location.longitude),
                sequence=item.sequence,
                observed_at=item.observed_at,
                ingested_at=item.ingested_at,
                online=item.online,
            )
            for item in payload.observations
        )
        previous: dict[str, LocationObservation] = {}
        assessments = []
        for observation in observations:
            result = assess_location(
                observation,
                previous.get(observation.courier_id),
                reference_time=payload.reference_time,
                max_speed_kilometres_per_hour=payload.max_speed_kilometres_per_hour,
                stale_after_seconds=payload.stale_after_seconds,
                max_ingestion_lag_seconds=payload.max_ingestion_lag_seconds,
            )
            assessments.append(
                LocationIntegrityResponse(
                    courier_id=result.courier_id,
                    status=result.status,
                    sequence=result.sequence,
                    distance_kilometres=result.distance_kilometres,
                    speed_kilometres_per_hour=result.speed_kilometres_per_hour,
                    staleness_seconds=result.staleness_seconds,
                    ingestion_lag_seconds=result.ingestion_lag_seconds,
                    sequence_gap=result.sequence_gap,
                    signals=tuple(
                        IntegritySignalResponse(
                            code=signal.code,
                            detail=signal.detail,
                            severity=signal.severity,
                        )
                        for signal in result.signals
                    ),
                    digest=result.digest,
                )
            )
            prior = previous.get(observation.courier_id)
            if prior is None or observation.sequence > prior.sequence:
                previous[observation.courier_id] = observation
        hotspots = build_hotspots(
            observations,
            cell_size_degrees=payload.hotspot_cell_size_degrees,
            minimum_unique_couriers=payload.minimum_hotspot_couriers,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return LocationIntegrityBatchResponse(
        source="compute",
        claim_label="operational signal; not a disciplinary action",
        assessments=tuple(assessments),
        hotspots=tuple(
            HotspotCellResponse(
                cell_id=cell.cell_id,
                latitude=cell.latitude,
                longitude=cell.longitude,
                observation_count=cell.observation_count,
                unique_courier_count=cell.unique_courier_count,
            )
            for cell in hotspots
        ),
        trace_id=trace_id,
    )


def _twin_state_response(state: TwinControlState, trace_id: str) -> TwinStateResponse:
    return TwinStateResponse(
        source="simulation",
        clock_domain=state.clock_domain,
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
        clock_domain=event.clock_domain,
        simulated_time_seconds=event.simulated_time_seconds,
        command_id=event.command_id,
        details=event.details,
    )


@router.get("/api/v1/twin/state", response_model=TwinStateResponse)
def twin_state(request: Request) -> TwinStateResponse:
    trace_id = getattr(request.state, "trace_id", "unavailable")
    return _twin_state_response(_runtime(request).twin_control.snapshot().state, trace_id)


@router.post("/api/v1/twin/control", response_model=TwinControlResponse)
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
        result = _runtime(request).twin_control.apply(command)
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


@router.get("/api/v1/strategies", response_model=tuple[StrategyDescriptorResponse, ...])
def strategy_catalog(request: Request) -> tuple[StrategyDescriptorResponse, ...]:
    return tuple(
        StrategyDescriptorResponse(
            name=descriptor.name,
            version=descriptor.version,
            capabilities=descriptor.capabilities,
            status="available",
            maturity=descriptor.maturity,
        )
        for descriptor in _registry(request).descriptors()
    )


@router.get(
    "/api/v1/strategies/{strategy_name}/parameters",
    response_model=StrategyParameterSchemaResponse,
)
def strategy_parameters(strategy_name: str, request: Request) -> StrategyParameterSchemaResponse:
    try:
        schema = _registry(request).parameter_schema(strategy_name)
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


@router.post("/api/v1/strategies/execute", response_model=StrategyExecutionResponse)
def execute_strategy(
    payload: StrategyExecutionRequest, request: Request
) -> StrategyExecutionResponse:
    trace_id = getattr(request.state, "trace_id", "unavailable")
    try:
        problem = _dispatch_problem(payload)
        decision = _registry(request).solve(payload.strategy, problem)
    except KeyError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except SolverOutputInvalidError as error:
        raise HTTPException(
            status_code=503,
            detail={
                **error.as_detail(),
                "trace_id": trace_id,
                "metadata": {
                    "requested_strategy": payload.strategy,
                    "fallback_strategy": "nearest",
                    "fallback_available": str("nearest" in _registry(request).names()).lower(),
                },
            },
        ) from error
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
                    "fallback_available": str("nearest" in _registry(request).names()).lower(),
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


@router.post("/api/v1/experiments/routebench", response_model=ExperimentResponse)
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
        registry = _registry(request)
        travel_provider = _runtime(request).travel_provider
        run = RouteBenchRunner(registry, travel_provider).run(manifest, scenario)
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


@router.post("/api/v1/experiments/what-if", response_model=WhatIfExperimentResponse)
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
        comparison = _runtime(request).what_if.run(
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


@router.post("/api/v1/shadow/evaluate", response_model=ShadowEvaluateResponse)
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
        run = ShadowModeEvaluator(_registry(request)).run(manifest, problems)
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


@router.post("/api/v1/dispatch/snapshot", response_model=DispatchSnapshotResponse)
def dispatch_snapshot(
    payload: DispatchSnapshotRequest, request: Request
) -> DispatchSnapshotResponse:
    trace_id = getattr(request.state, "trace_id", "unavailable")
    try:
        problem = _dispatch_problem(payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    try:
        decision = _registry(request).solve(payload.strategy, problem)
    except KeyError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except SolverOutputInvalidError as error:
        raise HTTPException(
            status_code=503,
            detail={
                **error.as_detail(),
                "trace_id": trace_id,
                "metadata": {
                    "fallback_strategy": "nearest",
                    "fallback_available": "true",
                },
            },
        ) from error
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
                _runtime(request).travel_provider.estimate(candidate.location, problem.pickup)
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
        clock_domain="WALL",
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
