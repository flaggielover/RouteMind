from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/compute-api/src"))

import r4_411b_google_live_validation as runner  # noqa: E402


class BrokenProvider:
    name = "broken-provider"

    def estimate(self, *args: object, **kwargs: object) -> object:
        raise RuntimeError("simulated provider failure")

    def matrix(self, *args: object, **kwargs: object) -> object:
        raise RuntimeError("simulated provider failure")


class ExplicitFallbackAdapter:
    """Dependency-free stand-in for the already-tested fallback policy."""

    def estimate(self, *args: object, **kwargs: object) -> object:
        return SimpleNamespace(
            fallback_used=True,
            fallback_reason="runtimeerror",
            provider="deterministic-local",
            seconds=123.0,
            distance_kilometres=None,
        )

    def matrix(self, *args: object, **kwargs: object) -> object:
        cell = SimpleNamespace(
            status="OK",
            error_class=None,
            seconds=123.0,
            distance_kilometres=None,
            fallback_used=True,
            provenance=(),
        )
        return SimpleNamespace(
            fallback_used=True,
            fallback_reason="runtimeerror",
            provider="deterministic-local",
            values=((cell, cell), (cell, cell)),
        )

class GoogleLiveValidationTests(unittest.TestCase):
    def test_budget_counts_and_rejects_matrix_element_overflow(self) -> None:
        budget = runner._Budget()
        budget.consume("ComputeRoutes")
        budget.consume("ComputeRouteMatrix", 4)
        self.assertEqual(budget.point_requests, 1)
        self.assertEqual(budget.matrix_requests, 1)
        self.assertEqual(budget.matrix_elements, 4)
        budget.matrix_elements = runner.MAX_MATRIX_ELEMENTS - 1
        with self.assertRaises(runner.ValidationAbort):
            budget.consume("ComputeRouteMatrix", 2)

    def test_point_and_matrix_use_explicit_fallback_without_hiding_reason(self) -> None:
        origin = SimpleNamespace(latitude=35.681236, longitude=139.767125)
        destination = SimpleNamespace(latitude=35.689592, longitude=139.700413)
        provider = ExplicitFallbackAdapter()
        budget = runner._Budget()
        point = runner._run_point(provider, origin, destination, budget)
        matrix = runner._run_matrix(provider, (origin,), (destination,), budget)
        self.assertEqual(point["status"], "FALLBACK")
        self.assertTrue(point["fallback_used"])
        self.assertEqual(point["fallback_provider"], "deterministic-local")
        self.assertEqual(matrix["status"], "FALLBACK")
        self.assertEqual(matrix["fallback_reason"], "runtimeerror")

    def test_evidence_writer_rejects_secret_and_writes_redacted_payload(self) -> None:
        evidence = {"secret_in_evidence": False, "status": "OK"}
        with tempfile.TemporaryDirectory() as directory, patch.object(
            runner, "EVIDENCE_DIR", Path(directory)
        ):
            path = runner._write_evidence(evidence, "opaque-test-secret")
            self.assertTrue(path.exists())
            with self.assertRaises(runner.ValidationAbort):
                runner._write_evidence({"value": "opaque-test-secret"}, "opaque-test-secret")

    def test_matrix_partial_cell_is_not_promoted_to_pass(self) -> None:
        cell_ok = SimpleNamespace(
            status="OK", error_class=None, seconds=10.0,
            distance_kilometres=1.0, fallback_used=False, provenance=()
        )
        cell_error = SimpleNamespace(
            status="ERROR", error_class="ROUTE_EXISTS", seconds=0.0,
            distance_kilometres=None, fallback_used=False, provenance=()
        )
        provider = SimpleNamespace(
            matrix=lambda *args, **kwargs: SimpleNamespace(
                fallback_used=False, values=((cell_ok, cell_error),), provider="google-routes"
            )
        )
        result = runner._run_matrix(provider, (object(),), (object(), object()), runner._Budget())
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["classification"], "partial_provider_response")


if __name__ == "__main__":
    unittest.main()
