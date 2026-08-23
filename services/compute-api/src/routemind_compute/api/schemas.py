from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from routemind_compute.application.twin_control import TwinAction


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["UP"]


class SystemInfoResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    service: Literal["compute-api"]
    runtime: Literal["python"]
    architecture_version: Literal["v1"]
    durable_state_owner: Literal[False]


class SemanticMetricDefinitionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    display_name: str
    description: str
    unit: str
    value_type: Literal["count", "ratio"]
    source_view: str
    source_fields: tuple[str, ...]
    aggregation: str
    numerator: str
    denominator: str | None
    time_semantics: str
    unavailable_when: str
    consumers: tuple[Literal["web", "report", "agent"], ...]
    definition_digest: str


class GeoPointRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class LocationObservationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    courier_id: str = Field(min_length=1, max_length=128)
    location: GeoPointRequest
    sequence: int = Field(gt=0)
    observed_at: datetime
    ingested_at: datetime
    online: bool = True


class LocationIntegrityRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    observations: tuple[LocationObservationRequest, ...] = Field(min_length=1, max_length=1000)
    reference_time: datetime | None = None
    max_speed_kilometres_per_hour: float = Field(default=130.0, gt=0, le=300)
    stale_after_seconds: float = Field(default=120.0, gt=0, le=86_400)
    max_ingestion_lag_seconds: float = Field(default=30.0, ge=0, le=86_400)
    hotspot_cell_size_degrees: float = Field(default=0.01, gt=0, le=1)
    minimum_hotspot_couriers: int = Field(default=3, ge=2, le=100)


class IntegritySignalResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    detail: str
    severity: Literal["info", "warning", "critical"]


class LocationIntegrityResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    courier_id: str
    status: Literal["HEALTHY", "DEGRADED", "SUSPECT", "STALE"]
    sequence: int
    distance_kilometres: float
    speed_kilometres_per_hour: float | None
    staleness_seconds: float
    ingestion_lag_seconds: float
    sequence_gap: int
    signals: tuple[IntegritySignalResponse, ...]
    digest: str


class HotspotCellResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    cell_id: str
    latitude: float
    longitude: float
    observation_count: int
    unique_courier_count: int


class LocationIntegrityBatchResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: Literal["compute"]
    claim_label: Literal["operational signal; not a disciplinary action"]
    assessments: tuple[LocationIntegrityResponse, ...]
    hotspots: tuple[HotspotCellResponse, ...]
    trace_id: str


class EtaPredictionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    order_id: str = Field(min_length=1, max_length=128)
    courier_id: str = Field(min_length=1, max_length=128)
    prediction_time: datetime
    horizon_seconds: float = Field(default=3600.0, gt=0, le=86_400)
    courier_location: GeoPointRequest
    pickup_location: GeoPointRequest
    delivery_location: GeoPointRequest
    courier_available_at: datetime
    pickup_ready_at: datetime
    preparation_seconds: float | None = Field(default=None, ge=0)
    pickup_seconds: float = Field(default=0.0, ge=0)
    delivery_seconds: float = Field(default=0.0, ge=0)
    actual_delivered_at: datetime | None = None


class EtaComponentResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    seconds: float | None
    source: str
    available: bool


class EtaPredictionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: Literal["compute"]
    claim_label: Literal["deterministic baseline; not calibrated production accuracy"]
    order_id: str
    courier_id: str
    prediction_time: datetime
    horizon_seconds: float
    predicted_delivery_at: datetime | None
    model: str
    model_version: str
    input_digest: str
    components: tuple[EtaComponentResponse, ...]
    outcome_available: bool
    actual_delivered_at: datetime | None
    actual_duration_seconds: float | None
    trace_id: str


class EtaCalibrationSampleRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    sample_id: str = Field(min_length=1, max_length=128)
    predicted_seconds: float = Field(ge=0)
    actual_seconds: float = Field(ge=0)
    interval_lower_seconds: float | None = Field(default=None, ge=0)
    interval_upper_seconds: float | None = Field(default=None, ge=0)


class EtaCalibrationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    samples: tuple[EtaCalibrationSampleRequest, ...] = Field(default=(), max_length=1000)
    predicted_seconds: float = Field(ge=0)
    sla_seconds: float = Field(gt=0)


class EtaCalibrationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: Literal["compute"]
    claim_label: Literal["calibration evidence only; not a customer guarantee"]
    status: Literal["AVAILABLE", "UNAVAILABLE"]
    sample_count: int
    mae_seconds: float | None
    median_error_seconds: float | None
    p90_error_seconds: float | None
    interval_coverage: float | None
    calibration_digest: str
    sla_status: Literal["ON_TRACK", "AT_RISK", "LIKELY_LATE"]
    predicted_seconds: float
    sla_seconds: float
    margin_seconds: float
    customer_confidence: Literal["available", "unavailable"]
    trace_id: str


class DelayAccountingComponentRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: Literal["dispatch", "travel", "preparation", "pickup", "delivery"]
    seconds: float | None = Field(default=None, ge=0)
    clock_domain: Literal["wall", "simulated"] | None = None


class DelayAccountingRecordRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    record_id: str = Field(min_length=1, max_length=128)
    observed_duration_seconds: float = Field(ge=0)
    clock_domain: Literal["wall", "simulated"]
    components: tuple[DelayAccountingComponentRequest, ...] = Field(default=(), max_length=5)


class DelayAccountingRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    records: tuple[DelayAccountingRecordRequest, ...] = Field(min_length=1, max_length=1000)


class DelayAccountingComponentResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: Literal["dispatch", "travel", "preparation", "pickup", "delivery"]
    seconds: float | None
    clock_domain: Literal["wall", "simulated"] | None


class DelayAccountingRecordResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    record_id: str
    status: Literal["RECONCILED", "UNRECONCILED", "INCOMPLETE", "CLOCK_DOMAIN_MISMATCH"]
    observed_duration_seconds: float
    accounted_duration_seconds: float
    residual_seconds: float | None
    components: tuple[DelayAccountingComponentResponse, ...]
    missing_components: tuple[str, ...]
    mismatched_components: tuple[str, ...]
    digest: str


class DelayAccountingAggregateResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    record_count: int
    observed_duration_seconds: float
    accounted_duration_seconds: float
    residual_seconds: float | None
    reconciled_count: int
    incomplete_count: int
    clock_domain_mismatch_count: int
    digest: str


class DelayAccountingResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: Literal["compute"]
    claim_label: Literal["accounting decomposition; not causal inference"]
    records: tuple[DelayAccountingRecordResponse, ...]
    aggregate: DelayAccountingAggregateResponse
    trace_id: str


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
    clock_domain: Literal["WALL"]
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
    maturity: Literal[
        "BASELINE", "ENGINEERING", "PRODUCTION-CANDIDATE", "RESEARCH", "EXTERNAL-VALIDATED"
    ]


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
    clock_domain: Literal["SIMULATED"]
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
    clock_domain: Literal["SIMULATED"]
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
