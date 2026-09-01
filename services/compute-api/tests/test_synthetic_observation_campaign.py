from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

import synthetic_observation_campaign as campaign  # noqa: E402  # type: ignore[import-not-found]


def test_campaign_manifest_binds_frozen_catalog_and_metric_boundary() -> None:
    catalog = campaign.load_catalog()
    manifest = campaign.build_campaign_manifest(catalog, (1, 2, 3))
    assert manifest["checkpoint"] == "RM-241"
    assert manifest["catalog_scenarios"] == list(campaign.EXPECTED_IDS)
    assert manifest["seeds_per_scenario"] == 3
    assert manifest["observation_schema"] == campaign.SCHEMA_VERSION
    unavailable = {
        item["name"]
        for item in manifest["preregistered_metrics"]
        if item["status"] == "UNAVAILABLE"
    }
    assert {"decision_latency", "solver_runtime", "sla_risk_delta"} <= unavailable
    assert manifest["raw_artifact"]["git_committed"] is False


def test_campaign_runs_all_frozen_scenarios_and_explains_candidates(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    output_dir = tmp_path / "artifacts"
    result = campaign.run_campaign(
        data_root=data_root,
        output_dir=output_dir,
        seeds=(17, 18),
    )
    registry = result["run_registry"]
    results = result["results"]
    assert registry["run_count"] == 16
    assert registry["observation_count"] > 0
    assert results["quality_status"] == "PASS"
    assert results["final_research_trigger"] == "NO_RESEARCH_TRIGGER"
    assert results["unexplained_residue_count"] == 0
    assert {item["anomaly_id"] for item in results["candidate_anomalies"]} == {"AD-001", "AD-002"}
    assert (data_root / "research-observations" / "policy-observations-v1.jsonl").exists()
    assert not list(output_dir.glob("*.jsonl"))
    exported_manifest = json.loads(
        (data_root / "research-observations" / "manifest-v1.json").read_text(encoding="utf-8")
    )
    assert exported_manifest["record_count"] == registry["observation_count"]
    assert exported_manifest["root_policy"] == "ROUTEMIND_DATA_ROOT"


def test_campaign_rerun_is_digest_stable(tmp_path: Path) -> None:
    first = campaign.run_campaign(
        data_root=tmp_path / "data-1",
        output_dir=tmp_path / "artifacts-1",
        seeds=(17, 18),
    )
    second = campaign.run_campaign(
        data_root=tmp_path / "data-2",
        output_dir=tmp_path / "artifacts-2",
        seeds=(17, 18),
    )
    assert first["results"] == second["results"]
    assert first["run_registry"]["runs"] == second["run_registry"]["runs"]
    assert first["export"].sha256 == second["export"].sha256


def test_existing_manifest_is_immutable(tmp_path: Path) -> None:
    output_dir = tmp_path / "artifacts"
    campaign.run_campaign(data_root=tmp_path / "data", output_dir=output_dir, seeds=(1, 2))
    manifest_path = output_dir / "CAMPAIGN_MANIFEST.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["strategy"] = "weighted-greedy"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="differs"):
        campaign.run_campaign(data_root=tmp_path / "data", output_dir=output_dir, seeds=(1, 2))


def test_seed_bound_is_enforced() -> None:
    with pytest.raises(ValueError, match="32"):
        campaign.build_campaign_manifest(campaign.load_catalog(), tuple(range(33)))
