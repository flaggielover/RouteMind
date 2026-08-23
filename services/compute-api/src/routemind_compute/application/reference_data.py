"""Immutable identities for reference data consumed by compute and analytics."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal

ReferenceDataKind = Literal["travel", "zone", "strategy", "analytical"]
_SAFE_NAME = re.compile(r"^[a-z][a-z0-9._-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REFERENCE_ID = re.compile(
    r"^(travel|zone|strategy|analytical):[a-z][a-z0-9._-]{0,127}:"
    r"[a-z][a-z0-9._-]{0,127}$"
)


class ReferenceDataError(ValueError):
    """Base contract error for reference-data identities."""


class ReferenceDataConflictError(ReferenceDataError):
    """Raised when an immutable identity is reused with different content."""


@dataclass(frozen=True, slots=True)
class ReferenceDataIdentity:
    """Content-addressed identity for one version of reference data."""

    kind: ReferenceDataKind
    name: str
    version: str
    content_digest: str
    producer: str
    supersedes: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in {"travel", "zone", "strategy", "analytical"}:
            raise ReferenceDataError(f"unsupported reference-data kind: {self.kind}")
        for value, label in (
            (self.name, "reference-data name"),
            (self.version, "reference-data version"),
            (self.producer, "reference-data producer"),
        ):
            if not isinstance(value, str) or not value.strip() or not _SAFE_NAME.fullmatch(value):
                raise ReferenceDataError(f"invalid {label}")
        if not _SHA256.fullmatch(self.content_digest):
            raise ReferenceDataError("reference-data content digest must be lowercase SHA-256")
        if self.supersedes is not None and not _REFERENCE_ID.fullmatch(self.supersedes):
            raise ReferenceDataError("reference-data supersedes identity is invalid")

    @property
    def reference_data_id(self) -> str:
        return f"{self.kind}:{self.name}:{self.version}"

    @property
    def digest(self) -> str:
        encoded = json.dumps(self.payload(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def payload(self) -> dict[str, str | None]:
        return {
            "reference_data_id": self.reference_data_id,
            "kind": self.kind,
            "name": self.name,
            "version": self.version,
            "content_digest": self.content_digest,
            "producer": self.producer,
            "supersedes": self.supersedes,
        }


class ReferenceDataCatalog:
    """In-process immutable catalog used by local fixtures and API adapters."""

    def __init__(self, identities: tuple[ReferenceDataIdentity, ...] = ()) -> None:
        self._identities: dict[str, ReferenceDataIdentity] = {}
        for identity in identities:
            self.register(identity)

    def register(self, identity: ReferenceDataIdentity) -> ReferenceDataIdentity:
        existing = self._identities.get(identity.reference_data_id)
        if existing is not None:
            if existing != identity:
                raise ReferenceDataConflictError(
                    f"reference-data identity is immutable: {identity.reference_data_id}"
                )
            return existing
        if identity.supersedes is not None and identity.supersedes not in self._identities:
            raise ReferenceDataError(
                f"superseded reference-data identity is missing: {identity.supersedes}"
            )
        self._identities[identity.reference_data_id] = identity
        return identity

    def get(self, reference_data_id: str) -> ReferenceDataIdentity:
        try:
            return self._identities[reference_data_id]
        except KeyError as error:
            raise ReferenceDataError(
                f"reference-data identity is not registered: {reference_data_id}"
            ) from error

    def snapshot(self) -> tuple[ReferenceDataIdentity, ...]:
        return tuple(self._identities[key] for key in sorted(self._identities))

    def link(self, reference_data_id: str) -> dict[str, str]:
        identity = self.get(reference_data_id)
        return {
            "reference_data_id": identity.reference_data_id,
            "reference_data_digest": identity.digest,
            "content_digest": identity.content_digest,
        }
