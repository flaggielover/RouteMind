from __future__ import annotations

import copy
import unittest

from disaster_recovery import (
    LOCAL_CLASSIFICATION,
    REQUIRED_CHECKS,
    TARGET_CLASSIFICATION,
    canonical_digest,
    external_identity_digest,
    qualify_report,
    validate_report,
)


def report(mode: str = "local-ci") -> dict[str, object]:
    target = mode == "target"
    external_identity = (
        {
            "provider": "Vultr",
            "region": "nrt",
            "resourceType": "Vultr Cloud Compute",
            "resourceId": "fixture-resource-id",
            "observedAt": "2026-08-25T12:00:00Z",
            "credentialedProviderEvidence": True,
            "executionManifestSha256": "e" * 64,
            "workloadDataClass": "SYNTHETIC_NO_CUSTOMER_DATA",
        }
        if target
        else None
    )
    value: dict[str, object] = {
        "schemaVersion": "r4-406.v1",
        "reportId": "fixture",
        "classification": TARGET_CLASSIFICATION if target else LOCAL_CLASSIFICATION,
        "productionDeploymentVerified": False,
        "environment": {
            "mode": mode,
            "provider": "Vultr" if target else "Docker",
            "region": "nrt" if target else "loopback",
            "targetEvidenceSha256": external_identity_digest(external_identity) if target else None,
        },
        "externalIdentity": external_identity,
        "safety": {
            "scope": "isolated_ephemeral_only",
            "productionDataUsed": False,
            "sourceContainersDestroyedBeforeRestore": True,
        },
        "artifacts": [
            {"service": service, "sha256": character * 64, "byteSize": index + 1}
            for index, (service, character) in enumerate((("postgres", "a"), ("rabbitmq", "b"), ("redis", "c")))
        ],
        "checks": {name: True for name in sorted(REQUIRED_CHECKS)},
        "metrics": {"rpoSeconds": 0, "rtoSeconds": 42.5, "rollbackSeconds": 7.0},
        "continuity": {"tenantCount": 2, "sourceDigest": "d" * 64, "restoredDigest": "d" * 64, "rollbackDigest": "d" * 64},
        "rollback": {"ack": "required", "manifestDigest": "f" * 64},
    }
    value["reportDigest"] = canonical_digest(value)
    return value


def mutate(value: dict[str, object], change) -> dict[str, object]:
    candidate = copy.deepcopy(value)
    change(candidate)
    candidate["reportDigest"] = canonical_digest(candidate)
    return candidate


class DisasterRecoveryTests(unittest.TestCase):
    def test_local_report_passes_but_never_qualifies_target(self) -> None:
        value = report()
        self.assertEqual(validate_report(value), ())
        self.assertEqual(qualify_report(value), "TARGET_NOT_QUALIFIED")
        self.assertIn("target_evidence_required", validate_report(value, require_target=True))

    def test_matching_target_report_qualifies_within_limits(self) -> None:
        value = report("target")
        self.assertEqual(validate_report(value, require_target=True), ())
        self.assertEqual(qualify_report(value), TARGET_CLASSIFICATION)

    def test_target_identity_and_thresholds_fail_closed(self) -> None:
        value = report("target")
        wrong_region = mutate(value, lambda item: item["environment"].update(region="ewr"))  # type: ignore[union-attr]
        excessive_rpo = mutate(value, lambda item: item["metrics"].update(rpoSeconds=901))  # type: ignore[union-attr]
        excessive_rto = mutate(value, lambda item: item["metrics"].update(rtoSeconds=7201))  # type: ignore[union-attr]
        uncredentialed = mutate(value, lambda item: item["externalIdentity"].update(credentialedProviderEvidence=False))  # type: ignore[union-attr]
        self.assertIn("target_identity", validate_report(wrong_region, require_target=True))
        self.assertIn("target_rpo_exceeded", validate_report(excessive_rpo, require_target=True))
        self.assertIn("target_rto_exceeded", validate_report(excessive_rto, require_target=True))
        self.assertIn("target_external_evidence", validate_report(uncredentialed, require_target=True))

    def test_claim_checks_and_artifacts_cannot_be_weakened(self) -> None:
        value = report()
        production = mutate(value, lambda item: item.update(productionDeploymentVerified=True))
        missing_check = mutate(value, lambda item: item["checks"].pop("inbox_restore"))  # type: ignore[union-attr]
        failed_check = mutate(value, lambda item: item["checks"].update(outbox_replay=False))  # type: ignore[union-attr]
        incomplete = mutate(value, lambda item: item.update(artifacts=item["artifacts"][:2]))  # type: ignore[index]
        self.assertIn("production_claim", validate_report(production))
        self.assertIn("check_set", validate_report(missing_check))
        self.assertIn("check_failure", validate_report(failed_check))
        self.assertIn("artifact_services", validate_report(incomplete))

    def test_continuity_rollback_safety_and_digest_are_bound(self) -> None:
        value = report()
        drift = mutate(value, lambda item: item["continuity"].update(restoredDigest="0" * 64))  # type: ignore[union-attr]
        unsafe = mutate(value, lambda item: item["safety"].update(productionDataUsed=True))  # type: ignore[union-attr]
        no_failure = mutate(value, lambda item: item["safety"].update(sourceContainersDestroyedBeforeRestore=False))  # type: ignore[union-attr]
        no_ack = mutate(value, lambda item: item["rollback"].update(ack="optional"))  # type: ignore[union-attr]
        stale = copy.deepcopy(value)
        stale["metrics"]["rtoSeconds"] = 10  # type: ignore[index]
        self.assertIn("durable_continuity", validate_report(drift))
        self.assertIn("safety_scope", validate_report(unsafe))
        self.assertIn("failure_boundary", validate_report(no_failure))
        self.assertIn("rollback_manifest", validate_report(no_ack))
        self.assertIn("report_digest", validate_report(stale))


if __name__ == "__main__":
    unittest.main()
