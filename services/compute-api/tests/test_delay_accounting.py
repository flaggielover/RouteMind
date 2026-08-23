import pytest

from routemind_compute.application.delay_accounting import (
    DelayAccountingComponent,
    DelayAccountingRecord,
    DelayClockDomain,
    account_record,
    account_records,
)


def components(
    clock_domain: DelayClockDomain = "wall", *, preparation: float | None = 30
) -> tuple[DelayAccountingComponent, ...]:
    return (
        DelayAccountingComponent("dispatch", 10, clock_domain),
        DelayAccountingComponent("travel", 20, clock_domain),
        DelayAccountingComponent(
            "preparation", preparation, clock_domain if preparation is not None else None
        ),
        DelayAccountingComponent("pickup", 5, clock_domain),
        DelayAccountingComponent("delivery", 65, clock_domain),
    )


def record(record_id: str = "order-1", *, observed: float = 130) -> DelayAccountingRecord:
    return DelayAccountingRecord(record_id, observed, "wall", components())


def test_accounting_reconciles_five_components_and_normalizes_order() -> None:
    result = account_record(record())

    assert result.status == "RECONCILED"
    assert result.accounted_duration_seconds == 130
    assert result.residual_seconds == 0
    assert [component.name for component in result.components] == [
        "dispatch",
        "travel",
        "preparation",
        "pickup",
        "delivery",
    ]
    assert len(result.digest) == 64


def test_accounting_marks_missing_and_unreconciled_duration_explicitly() -> None:
    incomplete = account_record(
        DelayAccountingRecord("missing", 120, "wall", components(preparation=None))
    )
    unreconciled = account_record(DelayAccountingRecord("residual", 131, "wall", components()))

    assert incomplete.status == "INCOMPLETE"
    assert incomplete.missing_components == ("preparation",)
    assert incomplete.residual_seconds == 20
    assert unreconciled.status == "UNRECONCILED"
    assert unreconciled.residual_seconds == 1


def test_accounting_marks_clock_mismatch_without_claiming_residual() -> None:
    mixed = list(components())
    mixed[1] = DelayAccountingComponent("travel", 20, "simulated")

    result = account_record(DelayAccountingRecord("mixed", 130, "wall", tuple(mixed)))

    assert result.status == "CLOCK_DOMAIN_MISMATCH"
    assert result.mismatched_components == ("travel",)
    assert result.residual_seconds is None


def test_accounting_aggregate_reconciles_totals_and_rejects_duplicate_ids() -> None:
    results, aggregate = account_records((record(), record("order-2", observed=131)))

    assert len(results) == 2
    assert aggregate.record_count == 2
    assert aggregate.observed_duration_seconds == 261
    assert aggregate.accounted_duration_seconds == 260
    assert aggregate.residual_seconds == 1
    assert aggregate.reconciled_count == 1
    with pytest.raises(ValueError, match="unique"):
        account_records((record(), record()))


def test_accounting_validates_identity_domains_and_components() -> None:
    with pytest.raises(ValueError, match="unknown"):
        DelayAccountingComponent("other", 1, "wall")
    with pytest.raises(ValueError, match="requires"):
        DelayAccountingComponent("travel", 1, None)
    with pytest.raises(ValueError, match="must not"):
        DelayAccountingComponent("travel", None, "wall")
    with pytest.raises(ValueError, match="unique"):
        DelayAccountingRecord("duplicate", 1, "wall", (components()[0], components()[0]))
    with pytest.raises(ValueError, match="duration"):
        DelayAccountingRecord("negative", -1, "wall", ())
