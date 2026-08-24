from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from routemind_compute.application import decision_corpus_cli
from routemind_compute.application.decision_corpus import (
    DecisionCorpus,
    DecisionCorpusError,
    ImmutableDecisionCorpusError,
    build_decision_corpus,
    load_decision_corpus,
    write_decision_corpus,
)

_DIGEST = "a" * 64


def _record(decision_id: str = "decision-1") -> dict[str, object]:
    return {
        "decision_id": decision_id,
        "state": {"state_digest": _DIGEST, "state_version": "state-v1"},
        "strategy": {"id": "shadow", "version": "2.1.0"},
        "candidates": [
            {
                "candidate_id": "courier-summary-1",
                "score": 0.25,
                "score_digest": _DIGEST,
                "feasible": True,
                "reason_code": "selected",
            },
            {
                "candidate_id": "courier-summary-2",
                "score": 0.75,
                "score_digest": "b" * 64,
                "feasible": False,
                "reason_code": "capacity",
            },
        ],
        "action": {"candidate_id": "courier-summary-1", "action_code": "assign"},
        "alternatives": [
            {
                "candidate_id": "courier-summary-2",
                "reason_code": "capacity",
                "score_digest": "b" * 64,
            }
        ],
        "objective": {
            "objective_id": "lateness-risk",
            "value": 0.25,
            "risk": 0.05,
            "objective_digest": "c" * 64,
        },
        "verification": {
            "status": "verified",
            "checks": ["capacity", "clock"],
            "verification_digest": "d" * 64,
        },
        "reference": {
            "reference_data_id": "travel:deterministic-local:v1",
            "version": "v1",
            "content_digest": "e" * 64,
        },
        "clock": {"domain": "SIMULATED", "event_time": "tick-42", "sequence": 42},
        "outcome": {
            "outcome_id": "outcome-1",
            "status": "accepted",
            "outcome_digest": "f" * 64,
        },
        "source_event_digest": "1" * 64,
    }


def _corpus(records: list[dict[str, object]] | None = None) -> DecisionCorpus:
    return build_decision_corpus(
        records or [_record()],
        corpus_id="fixture-r3-350",
        source_manifest_id="dispatch-ledger-fixture-v1",
        source_manifest_digest="2" * 64,
        code_revision="fixture-revision",
    )


def test_corpus_is_deterministic_and_round_trips_with_external_checksums(tmp_path: Path) -> None:
    first = _corpus([_record("decision-2"), _record("decision-1")])
    second = _corpus([_record("decision-1"), _record("decision-2")])
    assert first.manifest_digest == second.manifest_digest
    assert first.records_bytes == second.records_bytes

    manifest_path = write_decision_corpus(first, tmp_path)
    loaded = load_decision_corpus(manifest_path.parent)
    assert loaded.manifest_digest == first.manifest_digest
    assert loaded.records == first.records
    assert (
        manifest_path.with_suffix(".json.sha256").read_text(encoding="ascii").strip()
        == hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    )


def test_corpus_preserves_linkage_but_rejects_raw_trajectory_fields() -> None:
    corpus = _corpus()
    record = corpus.records[0]
    assert set(record) == {
        "decision_id",
        "state",
        "strategy",
        "candidates",
        "action",
        "alternatives",
        "objective",
        "verification",
        "reference",
        "clock",
        "outcome",
        "source_event_digest",
        "record_digest",
    }
    source = _record()
    source["raw_trajectory"] = [{"latitude": 1.0, "longitude": 2.0}]
    with pytest.raises(DecisionCorpusError, match="privacy-forbidden"):
        _corpus([source])


def test_corpus_rejects_missing_fields_duplicate_decisions_and_bad_action() -> None:
    source = _record()
    del source["outcome"]
    with pytest.raises(DecisionCorpusError, match="fields mismatch"):
        _corpus([source])
    with pytest.raises(DecisionCorpusError, match="unique"):
        _corpus([_record(), _record()])
    source = _record()
    source["action"] = {"candidate_id": "missing", "action_code": "assign"}
    with pytest.raises(DecisionCorpusError, match="present in candidates"):
        _corpus([source])


def test_corpus_is_write_once_and_detects_tampering(tmp_path: Path) -> None:
    corpus = _corpus()
    manifest = write_decision_corpus(corpus, tmp_path)
    assert write_decision_corpus(corpus, tmp_path) == manifest
    records = manifest.parent / "records.jsonl"
    records.write_text(records.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(DecisionCorpusError, match="checksum"):
        load_decision_corpus(manifest.parent)
    records.write_bytes(corpus.records_bytes)
    different = _corpus([_record("different")])
    with pytest.raises(ImmutableDecisionCorpusError, match="differs"):
        write_decision_corpus(different, tmp_path)


def test_corpus_rejects_unsafe_identity_and_non_finite_values() -> None:
    with pytest.raises(DecisionCorpusError, match="unsafe"):
        build_decision_corpus(
            [_record()],
            corpus_id="../unsafe",
            source_manifest_id="source",
            source_manifest_digest="2" * 64,
            code_revision="revision",
        )
    source = _record()
    source["objective"] = {
        "objective_id": "lateness-risk",
        "value": float("nan"),
        "risk": 0.05,
        "objective_digest": "c" * 64,
    }
    with pytest.raises(DecisionCorpusError, match="finite"):
        _corpus([source])


def test_corpus_manifest_is_canonical_json() -> None:
    corpus = _corpus()
    parsed = json.loads(corpus.records_bytes.decode("utf-8"))
    assert parsed["decision_id"] == "decision-1"


def test_corpus_cli_writes_external_artifact(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = {
        "corpus_id": "cli-fixture",
        "source_manifest_id": "source-fixture",
        "source_manifest_digest": "2" * 64,
        "code_revision": "cli-test",
        "records": [_record()],
    }
    input_path = tmp_path / "source.json"
    input_path.write_text(json.dumps(source), encoding="utf-8")
    assert decision_corpus_cli.main(["--input", str(input_path), "--data-root", str(tmp_path)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["record_count"] == 1
    assert Path(output["manifest_path"]).is_file()
