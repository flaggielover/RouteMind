from __future__ import annotations

import pytest

from routemind_compute.application.parameters import (
    ParameterDefinition,
    StrategyParameterSchema,
    schema_for,
)


def test_parameter_schema_normalizes_defaults_and_values() -> None:
    schema = schema_for("weighted-greedy", "1.0.0")
    assert schema.validate(()) == (("distance_weight", "1"),)
    assert schema.validate((("distance_weight", "2.500"),)) == (("distance_weight", "2.5"),)
    assert schema.canonical_payload()["strategy"] == "weighted-greedy"


def test_parameter_schema_rejects_unknown_duplicate_and_invalid_values() -> None:
    schema = schema_for("risk-aware", "1.0.0")
    with pytest.raises(ValueError, match="unknown"):
        schema.validate((("missing", "1"),))
    with pytest.raises(ValueError, match="unique"):
        schema.validate((("distance", "1"), ("distance", "2")))
    with pytest.raises(ValueError, match="finite"):
        schema.validate((("distance", "nan"),))
    with pytest.raises(ValueError, match="below"):
        schema.validate((("distance", "-1"),))


def test_parameter_definitions_and_empty_strategy_schema_validate_invariants() -> None:
    with pytest.raises(ValueError, match="identity"):
        ParameterDefinition(" ", "float", "1")
    with pytest.raises(ValueError, match="default"):
        ParameterDefinition("weight", "float", "nan")
    with pytest.raises(ValueError, match="unique"):
        StrategyParameterSchema(
            "demo",
            "1.0.0",
            (ParameterDefinition("x", "float", "1"), ParameterDefinition("x", "float", "2")),
        )
    assert schema_for("nearest", "1.0.0").validate(()) == ()
