from __future__ import annotations

import threading
import time

import pytest

from routemind_compute.application.r4_experiment_scheduler import (
    ExperimentManifest,
    ExperimentScheduler,
    ScheduleAudit,
    SchedulerPolicy,
)


def manifest(**overrides: object) -> ExperimentManifest:
    values: dict[str, object] = {
        "manifest_id": "r4-430-fixture",
        "code_revision": "fixture-revision",
        "scenario_id": "scenario-baseline",
        "resource_units": 1,
        "concurrency": 1,
        "timeout_seconds": 0.2,
        "lineage": ("R3-330", "R4-430"),
        "evidence_targets": (),
    }
    values.update(overrides)
    return ExperimentManifest.create(**values)  # type: ignore[arg-type]


def test_manifest_is_content_addressed_and_completed_output_is_audited() -> None:
    scheduler = ExperimentScheduler()
    first = scheduler.run(manifest(), lambda cancel: {"value": 7})
    second = scheduler.run(manifest(), lambda cancel: {"value": 7})

    assert first.status == "COMPLETED"
    assert first.output_digest == second.output_digest
    assert first.lineage_digest == second.lineage_digest
    assert first.sequence == 1 and second.sequence == 2


def test_admission_rejects_resource_timeout_manifest_and_frozen_evidence() -> None:
    frozen = {"r3/frozen.json": "a" * 64}
    scheduler = ExperimentScheduler(
        SchedulerPolicy(max_resource_units=2, max_timeout_seconds=0.1), frozen_evidence=frozen
    )
    assert (
        scheduler.run(manifest(resource_units=3), lambda cancel: None).reason
        == "resource_limit_exceeded"
    )
    assert (
        scheduler.run(manifest(timeout_seconds=0.2), lambda cancel: None).reason
        == "timeout_limit_exceeded"
    )
    assert (
        scheduler.run(
            manifest(timeout_seconds=0.05, evidence_targets=("r3/frozen.json",)),
            lambda cancel: None,
        ).reason
        == "frozen_evidence_target_forbidden"
    )


def test_cancel_timeout_failure_and_invalid_output_are_explicit() -> None:
    scheduler = ExperimentScheduler()
    cancelled = threading.Event()
    cancelled.set()
    assert (
        scheduler.run(manifest(), lambda cancel: None, cancel_event=cancelled).status == "CANCELLED"
    )

    def slow(cancel: threading.Event) -> None:
        time.sleep(0.05)

    timed_out = scheduler.run(manifest(timeout_seconds=0.001), slow)
    assert timed_out.status == "TIMED_OUT"

    failed = scheduler.run(manifest(), lambda cancel: (_ for _ in ()).throw(RuntimeError("boom")))
    assert failed.status == "FAILED"

    invalid = scheduler.run(manifest(), lambda cancel: float("nan"))
    assert invalid.status == "FAILED"


def test_concurrency_limit_is_enforced_without_mutating_audit() -> None:
    scheduler = ExperimentScheduler(SchedulerPolicy(max_concurrency=1))
    entered = threading.Event()
    release = threading.Event()

    def waiting(cancel: threading.Event) -> None:
        entered.set()
        release.wait(0.2)

    result: list[ScheduleAudit] = []
    worker = threading.Thread(target=lambda: result.append(scheduler.run(manifest(), waiting)))
    worker.start()
    assert entered.wait(0.2)
    rejected = scheduler.run(manifest(), lambda cancel: None)
    release.set()
    worker.join(1)
    assert rejected.reason == "concurrency_limit_exceeded"
    assert result and result[0].status == "COMPLETED"


def test_manifest_rejects_digest_tampering_and_invalid_policy() -> None:
    valid = manifest()
    with pytest.raises(ValueError, match="manifest_digest"):
        ExperimentManifest(
            valid.manifest_id,
            valid.code_revision,
            valid.scenario_id,
            valid.resource_units,
            valid.concurrency,
            valid.timeout_seconds,
            valid.lineage,
            "b" * 64,
            valid.evidence_targets,
        )
    with pytest.raises(ValueError):
        SchedulerPolicy(max_resource_units=0)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("manifest_id", "", "manifest_id"),
        ("manifest_id", "bad value", "manifest_id"),
        ("resource_units", 0, "resource_units"),
        ("concurrency", 0, "concurrency"),
        ("timeout_seconds", 0.0, "timeout_seconds"),
        ("lineage", (), "lineage"),
        ("lineage", ("R3-330", "R3-330"), "lineage entries"),
        ("evidence_targets", ("",), "evidence_targets"),
        ("evidence_targets", ("evidence.json", "evidence.json"), "evidence_targets"),
    ],
)
def test_manifest_boundaries_fail_closed(field: str, value: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        manifest(**{field: value})


def test_scheduler_policy_and_frozen_evidence_validate_limits() -> None:
    with pytest.raises(ValueError, match="max_timeout_seconds"):
        SchedulerPolicy(max_timeout_seconds=0)
    with pytest.raises(ValueError, match="frozen evidence"):
        ExperimentScheduler(frozen_evidence={"evidence.json": "not-a-digest"})
    scheduler = ExperimentScheduler(SchedulerPolicy(max_concurrency=2, max_timeout_seconds=1))
    assert scheduler.run(manifest(concurrency=3), lambda cancel: None).reason == (
        "manifest_concurrency_exceeded"
    )
    assert scheduler.audits


def test_operation_cancellation_is_recorded_after_start() -> None:
    scheduler = ExperimentScheduler()

    def cancel(cancel_event: threading.Event) -> None:
        cancel_event.set()

    result = scheduler.run(manifest(), cancel)
    assert result.status == "CANCELLED"
    assert result.reason == "cancelled"
