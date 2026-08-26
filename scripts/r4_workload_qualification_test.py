from __future__ import annotations

import io
import json
import unittest
import uuid
from contextlib import redirect_stdout
from unittest.mock import patch

import r4_workload_qualification as qualification


class WorkloadQualificationTest(unittest.TestCase):
    def test_main_uses_java_compatible_correlation_and_real_operations(self) -> None:
        requests: list[tuple[str, dict, dict[str, str]]] = []

        def fake_post(url: str, payload: dict, headers: dict[str, str]) -> dict:
            requests.append((url, payload, headers))
            if url.endswith("/api/v1/orders"):
                return {"status": "CREATED"}
            if url.endswith("/api/v1/twin/control"):
                return {"source": "simulation"}
            if url.endswith("/api/v1/experiments/routebench"):
                return {"source": "experiment"}
            raise AssertionError(f"unexpected URL: {url}")

        output = io.StringIO()
        with (
            patch.object(qualification, "_post", side_effect=fake_post),
            patch.object(qualification.time, "sleep"),
            patch.dict(
                qualification.os.environ,
                {
                    "ROUTEMIND_QUALIFICATION_ID": "unit",
                    "ROUTEMIND_SOURCE_REVISION": "abc123",
                },
                clear=False,
            ),
            redirect_stdout(output),
        ):
            self.assertEqual(0, qualification.main())

        self.assertEqual(3, len(requests))
        correlation_ids = {request[2]["X-Correlation-Id"] for request in requests}
        self.assertEqual(1, len(correlation_ids))
        uuid.UUID(next(iter(correlation_ids)))
        self.assertTrue(
            all(request[2]["traceparent"].startswith("00-") for request in requests)
        )
        result = json.loads(output.getvalue())
        self.assertTrue(result["actualRouteMindWorkload"])
        self.assertEqual("abc123", result["sourceRevision"])


if __name__ == "__main__":
    unittest.main()
