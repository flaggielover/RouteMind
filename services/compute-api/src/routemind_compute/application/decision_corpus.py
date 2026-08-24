"""Privacy-bounded, content-addressed research Decision Corpus artifacts."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from pathlib import Path

from routemind_compute.application.execution import canonical_digest

_SCHEMA = "routemind-decision-corpus-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CORPUS_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_FORBIDDEN_KEY = re.compile(
    r"(^|_)(address|customer|email|gps|lat|latitude|location|lon|longitude|name|phone|"
    r"precise|raw|trajectory|trace)(_|$)"
)
_TOP_LEVEL = frozenset(
    {
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
    }
)


class DecisionCorpusError(ValueError):
    """Raised when a corpus record or artifact is unsafe or inconsistent."""


class ImmutableDecisionCorpusError(DecisionCorpusError):
    """Raised when a content-addressed corpus would be overwritten."""


@dataclass(frozen=True, slots=True)
class DecisionCorpusPolicy:
    """The allow-list and retention contract for research decision records."""

    policy_id: str = "r3-350-decision-corpus-retention-v1"
    max_records: int = 100_000
    excluded_fields: tuple[str, ...] = (
        "raw_payload",
        "raw_trajectory",
        "coordinates",
        "direct_identifiers",
    )

    def __post_init__(self) -> None:
        if not self.policy_id.strip() or self.max_records <= 0:
            raise DecisionCorpusError("corpus policy is invalid")

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "max_records": self.max_records,
            "excluded_fields": self.excluded_fields,
            "retention_mode": "research-summary-only",
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload())


@dataclass(frozen=True, slots=True)
class DecisionCorpus:
    corpus_id: str
    source_manifest_id: str
    source_manifest_digest: str
    code_revision: str
    policy: DecisionCorpusPolicy
    records: tuple[Mapping[str, object], ...]
    records_bytes: bytes
    records_sha256: str
    records_digest: str
    manifest_digest: str

    def manifest_payload(self) -> dict[str, object]:
        return {
            "schema": _SCHEMA,
            "corpus_id": self.corpus_id,
            "source_manifest_id": self.source_manifest_id,
            "source_manifest_digest": self.source_manifest_digest,
            "code_revision": self.code_revision,
            "policy": self.policy.payload(),
            "policy_digest": self.policy.digest,
            "record_count": len(self.records),
            "record_digests": [str(record["record_digest"]) for record in self.records],
            "records_digest": self.records_digest,
            "records_sha256": self.records_sha256,
            "manifest_digest": self.manifest_digest,
            "records_file": "records.jsonl",
            "retention_boundary": "no_raw_trajectories_or_direct_identifiers",
        }


def build_decision_corpus(
    records: Iterable[Mapping[str, object]],
    *,
    corpus_id: str,
    source_manifest_id: str,
    source_manifest_digest: str,
    code_revision: str,
    policy: DecisionCorpusPolicy | None = None,
) -> DecisionCorpus:
    """Normalize a bounded source iterable without executing or replaying decisions."""

    _require_id(corpus_id, "corpus_id", _CORPUS_ID)
    _require_text(source_manifest_id, "source_manifest_id")
    _require_digest(source_manifest_digest, "source_manifest_digest")
    _require_text(code_revision, "code_revision")
    selected_policy = policy or DecisionCorpusPolicy()
    normalized = tuple(sorted((_normalize_record(item) for item in records), key=_record_key))
    if not normalized:
        raise DecisionCorpusError("decision corpus must contain at least one record")
    if len(normalized) > selected_policy.max_records:
        raise DecisionCorpusError("decision corpus exceeds the retention record limit")
    ids = [str(item["decision_id"]) for item in normalized]
    if len(ids) != len(set(ids)):
        raise DecisionCorpusError("decision_id values must be unique")
    encoded = b"".join(_canonical_json(item).encode("utf-8") + b"\n" for item in normalized)
    records_digest = canonical_digest(list(normalized))
    records_sha256 = sha256(encoded).hexdigest()
    manifest_core = {
        "schema": _SCHEMA,
        "corpus_id": corpus_id,
        "source_manifest_id": source_manifest_id,
        "source_manifest_digest": source_manifest_digest,
        "code_revision": code_revision,
        "policy": selected_policy.payload(),
        "policy_digest": selected_policy.digest,
        "record_count": len(normalized),
        "record_digests": [str(item["record_digest"]) for item in normalized],
        "records_digest": records_digest,
        "records_sha256": records_sha256,
        "records_file": "records.jsonl",
        "retention_boundary": "no_raw_trajectories_or_direct_identifiers",
    }
    return DecisionCorpus(
        corpus_id,
        source_manifest_id,
        source_manifest_digest,
        code_revision,
        selected_policy,
        normalized,
        encoded,
        records_sha256,
        records_digest,
        canonical_digest(manifest_core),
    )


def write_decision_corpus(corpus: DecisionCorpus, data_root: Path | str) -> Path:
    """Write a corpus below the external data root using write-once semantics."""

    root = Path(data_root).expanduser().resolve()
    target = root / "research" / "r3" / "R3-350" / corpus.corpus_id
    target.mkdir(parents=True, exist_ok=True)
    records_path = target / "records.jsonl"
    manifest_path = target / "manifest.json"
    manifest_bytes = (_canonical_json(corpus.manifest_payload()) + "\n").encode("utf-8")
    expected = ((records_path, corpus.records_bytes), (manifest_path, manifest_bytes))
    for path, content in expected:
        sidecar = path.with_suffix(path.suffix + ".sha256")
        if path.exists() or sidecar.exists():
            if not path.is_file() or not sidecar.is_file() or path.read_bytes() != content:
                raise ImmutableDecisionCorpusError(f"existing corpus artifact differs: {path.name}")
            if sidecar.read_text(encoding="ascii").strip() != sha256(content).hexdigest():
                raise ImmutableDecisionCorpusError(
                    f"corpus checksum sidecar is invalid: {path.name}"
                )
            continue
        path.write_bytes(content)
        sidecar.write_text(sha256(content).hexdigest() + "\n", encoding="ascii", newline="\n")
    return manifest_path


def load_decision_corpus(directory: Path | str) -> DecisionCorpus:
    """Verify and load a previously written corpus without modifying it."""

    target = Path(directory).expanduser().resolve()
    manifest_path = target / "manifest.json"
    records_path = target / "records.jsonl"
    manifest = _read_json(manifest_path)
    _verify_sidecar(manifest_path)
    _verify_sidecar(records_path)
    if manifest.get("schema") != _SCHEMA or manifest.get("records_file") != "records.jsonl":
        raise DecisionCorpusError("corpus manifest schema is unsupported")
    record_lines = records_path.read_bytes()
    if sha256(record_lines).hexdigest() != _text(manifest, "records_sha256"):
        raise DecisionCorpusError("corpus records checksum does not match manifest")
    parsed = tuple(
        _read_record(line, number)
        for number, line in enumerate(record_lines.decode("utf-8").splitlines(), start=1)
    )
    if len(parsed) != _integer(manifest, "record_count"):
        raise DecisionCorpusError("corpus record count does not match manifest")
    if canonical_digest(list(parsed)) != _text(manifest, "records_digest"):
        raise DecisionCorpusError("corpus record digest does not match manifest")
    expected_digests = tuple(str(item) for item in _sequence(manifest, "record_digests"))
    if tuple(str(item["record_digest"]) for item in parsed) != expected_digests:
        raise DecisionCorpusError("corpus record digest list does not match manifest")
    manifest_core = dict(manifest)
    manifest_digest = _text(manifest_core, "manifest_digest")
    del manifest_core["manifest_digest"]
    if canonical_digest(manifest_core) != manifest_digest:
        raise DecisionCorpusError("corpus manifest digest does not match content")
    policy_payload = _mapping(manifest, "policy")
    policy = DecisionCorpusPolicy(
        policy_id=_text(policy_payload, "policy_id"),
        max_records=_integer(policy_payload, "max_records"),
        excluded_fields=tuple(str(item) for item in _sequence(policy_payload, "excluded_fields")),
    )
    if policy.digest != _text(manifest, "policy_digest"):
        raise DecisionCorpusError("corpus policy digest does not match manifest")
    return DecisionCorpus(
        _text(manifest, "corpus_id"),
        _text(manifest, "source_manifest_id"),
        _text(manifest, "source_manifest_digest"),
        _text(manifest, "code_revision"),
        policy,
        parsed,
        record_lines,
        _text(manifest, "records_sha256"),
        _text(manifest, "records_digest"),
        manifest_digest,
    )


def _normalize_record(value: Mapping[str, object]) -> dict[str, object]:
    _scan_forbidden(value)
    if set(value) != _TOP_LEVEL:
        missing = sorted(_TOP_LEVEL - set(value))
        extra = sorted(set(value) - _TOP_LEVEL)
        raise DecisionCorpusError(f"record fields mismatch; missing={missing}, extra={extra}")
    candidates = _candidates(_sequence(value, "candidates"))
    action = _action(_mapping(value, "action"))
    record: dict[str, object] = {
        "decision_id": _text(value, "decision_id"),
        "state": _state(_mapping(value, "state")),
        "strategy": _strategy(_mapping(value, "strategy")),
        "candidates": candidates,
        "action": action,
        "alternatives": _alternatives(_sequence(value, "alternatives")),
        "objective": _objective(_mapping(value, "objective")),
        "verification": _verification(_mapping(value, "verification")),
        "reference": _reference(_mapping(value, "reference")),
        "clock": _clock(_mapping(value, "clock")),
        "outcome": _outcome(_mapping(value, "outcome")),
        "source_event_digest": _text_digest(value, "source_event_digest"),
    }
    if not any(item["candidate_id"] == action["candidate_id"] for item in candidates):
        raise DecisionCorpusError("action candidate_id must be present in candidates")
    record["record_digest"] = canonical_digest(record)
    return record


def _state(value: Mapping[str, object]) -> dict[str, object]:
    _exact(value, {"state_digest", "state_version"}, "state")
    return {
        "state_digest": _text_digest(value, "state_digest"),
        "state_version": _text(value, "state_version"),
    }


def _strategy(value: Mapping[str, object]) -> dict[str, object]:
    _exact(value, {"id", "version"}, "strategy")
    return {"id": _text(value, "id"), "version": _text(value, "version")}


def _candidates(value: Sequence[object]) -> list[dict[str, object]]:
    if not value or len(value) > 512:
        raise DecisionCorpusError("candidates must contain between one and 512 summaries")
    result: list[dict[str, object]] = []
    for item in value:
        candidate = _mapping_value(item, "candidate")
        _exact(
            candidate,
            {"candidate_id", "score", "score_digest", "feasible", "reason_code"},
            "candidate",
        )
        result.append(
            {
                "candidate_id": _text(candidate, "candidate_id"),
                "score": _number(candidate, "score"),
                "score_digest": _text_digest(candidate, "score_digest"),
                "feasible": _bool(candidate, "feasible"),
                "reason_code": _text(candidate, "reason_code"),
            }
        )
    ids = [str(item["candidate_id"]) for item in result]
    if len(ids) != len(set(ids)):
        raise DecisionCorpusError("candidate_id values must be unique")
    return sorted(result, key=lambda item: str(item["candidate_id"]))


def _action(value: Mapping[str, object]) -> dict[str, object]:
    _exact(value, {"candidate_id", "action_code"}, "action")
    return {
        "candidate_id": _text(value, "candidate_id"),
        "action_code": _text(value, "action_code"),
    }


def _alternatives(value: Sequence[object]) -> list[dict[str, object]]:
    if len(value) > 512:
        raise DecisionCorpusError("alternatives exceed the retention limit")
    result: list[dict[str, object]] = []
    for item in value:
        alternative = _mapping_value(item, "alternative")
        _exact(alternative, {"candidate_id", "reason_code", "score_digest"}, "alternative")
        result.append(
            {
                "candidate_id": _text(alternative, "candidate_id"),
                "reason_code": _text(alternative, "reason_code"),
                "score_digest": _text_digest(alternative, "score_digest"),
            }
        )
    return sorted(result, key=lambda item: (str(item["candidate_id"]), str(item["reason_code"])))


def _objective(value: Mapping[str, object]) -> dict[str, object]:
    _exact(value, {"objective_id", "value", "risk", "objective_digest"}, "objective")
    return {
        "objective_id": _text(value, "objective_id"),
        "value": _number(value, "value"),
        "risk": _number(value, "risk"),
        "objective_digest": _text_digest(value, "objective_digest"),
    }


def _verification(value: Mapping[str, object]) -> dict[str, object]:
    _exact(value, {"status", "checks", "verification_digest"}, "verification")
    checks = tuple(
        sorted(_text_item(item, "verification check") for item in _sequence(value, "checks"))
    )
    return {
        "status": _text(value, "status"),
        "checks": checks,
        "verification_digest": _text_digest(value, "verification_digest"),
    }


def _reference(value: Mapping[str, object]) -> dict[str, object]:
    _exact(value, {"reference_data_id", "version", "content_digest"}, "reference")
    return {
        "reference_data_id": _text(value, "reference_data_id"),
        "version": _text(value, "version"),
        "content_digest": _text_digest(value, "content_digest"),
    }


def _clock(value: Mapping[str, object]) -> dict[str, object]:
    _exact(value, {"domain", "event_time", "sequence"}, "clock")
    domain = _text(value, "domain")
    if domain not in {"WALL", "SIMULATED", "REPLAY"}:
        raise DecisionCorpusError("clock domain is unsupported")
    return {
        "domain": domain,
        "event_time": _text(value, "event_time"),
        "sequence": _integer(value, "sequence"),
    }


def _outcome(value: Mapping[str, object]) -> dict[str, object]:
    _exact(value, {"outcome_id", "status", "outcome_digest"}, "outcome")
    return {
        "outcome_id": _text(value, "outcome_id"),
        "status": _text(value, "status"),
        "outcome_digest": _text_digest(value, "outcome_digest"),
    }


def _record_key(value: Mapping[str, object]) -> str:
    return str(value["decision_id"])


def _scan_forbidden(value: object) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "_")
            if _FORBIDDEN_KEY.search(normalized):
                raise DecisionCorpusError(f"privacy-forbidden field: {key}")
            _scan_forbidden(item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            _scan_forbidden(item)


def _exact(value: Mapping[str, object], allowed: set[str], label: str) -> None:
    if set(value) != allowed:
        raise DecisionCorpusError(f"{label} fields mismatch")


def _mapping(value: Mapping[str, object], key: str) -> Mapping[str, object]:
    return _mapping_value(value.get(key), key)


def _mapping_value(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise DecisionCorpusError(f"{label} must be an object")
    return value


def _sequence(value: Mapping[str, object], key: str) -> Sequence[object]:
    selected = value.get(key)
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray)):
        raise DecisionCorpusError(f"{key} must be an array")
    return selected


def _text(value: Mapping[str, object], key: str) -> str:
    return _text_item(value.get(key), key)


def _text_item(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > 512
        or any(ord(char) < 32 for char in value)
    ):
        raise DecisionCorpusError(f"{label} must be non-empty text")
    return value


def _require_text(value: str, label: str) -> None:
    _text_item(value, label)


def _require_id(value: str, label: str, pattern: re.Pattern[str]) -> None:
    _require_text(value, label)
    if not pattern.fullmatch(value):
        raise DecisionCorpusError(f"{label} has unsafe characters")


def _text_digest(value: Mapping[str, object], key: str) -> str:
    selected = _text(value, key)
    _require_digest(selected, key)
    return selected


def _require_digest(value: str, label: str) -> None:
    if not _SHA256.fullmatch(value):
        raise DecisionCorpusError(f"{label} must be a lowercase SHA-256 digest")


def _number(value: Mapping[str, object], key: str) -> float:
    selected = value.get(key)
    if (
        isinstance(selected, bool)
        or not isinstance(selected, (int, float))
        or not isfinite(float(selected))
    ):
        raise DecisionCorpusError(f"{key} must be a finite number")
    return float(selected)


def _bool(value: Mapping[str, object], key: str) -> bool:
    selected = value.get(key)
    if not isinstance(selected, bool):
        raise DecisionCorpusError(f"{key} must be boolean")
    return selected


def _integer(value: Mapping[str, object], key: str) -> int:
    selected = value.get(key)
    if isinstance(selected, bool) or not isinstance(selected, int):
        raise DecisionCorpusError(f"{key} must be an integer")
    return selected


def _read_json(path: Path) -> dict[str, object]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DecisionCorpusError(f"cannot read corpus manifest: {path}") from exc
    return dict(_mapping_value(parsed, "manifest"))


def _verify_sidecar(path: Path) -> None:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not path.is_file() or not sidecar.is_file():
        raise DecisionCorpusError(f"corpus artifact or checksum sidecar is missing: {path.name}")
    if sidecar.read_text(encoding="ascii").strip() != sha256(path.read_bytes()).hexdigest():
        raise DecisionCorpusError(f"corpus checksum mismatch: {path.name}")


def _read_record(line: str, number: int) -> dict[str, object]:
    try:
        parsed = json.loads(line)
    except json.JSONDecodeError as exc:
        raise DecisionCorpusError(f"invalid corpus record at line {number}") from exc
    if not isinstance(parsed, Mapping):
        raise DecisionCorpusError(f"corpus record at line {number} is not an object")
    normalized = _normalize_record(
        {key: value for key, value in parsed.items() if key != "record_digest"}
    )
    if parsed.get("record_digest") != normalized["record_digest"]:
        raise DecisionCorpusError(f"record digest mismatch at line {number}")
    return normalized


def _canonical_json(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=True, allow_nan=False, separators=(",", ":"), sort_keys=True
    )


__all__ = [
    "DecisionCorpus",
    "DecisionCorpusError",
    "DecisionCorpusPolicy",
    "ImmutableDecisionCorpusError",
    "build_decision_corpus",
    "load_decision_corpus",
    "write_decision_corpus",
]
