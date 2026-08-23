from __future__ import annotations

import concurrent.futures
import hashlib
import json
import platform
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5


SEED = 18023
BUSINESS = "http://127.0.0.1:18080"
COMPUTE = "http://127.0.0.1:18081"


@dataclass(frozen=True)
class Result:
    status: int
    body: object
    elapsed_ms: float


def request(method: str, url: str, body: object | None = None, headers: dict[str, str] | None = None,
            timeout: float = 10.0) -> Result:
    encoded = None if body is None else json.dumps(body, separators=(",", ":")).encode()
    request_headers = {"X-Trace-Id": "0123456789abcdef0123456789abcdef"}
    if headers:
        request_headers.update(headers)
    if encoded is not None:
        request_headers["Content-Type"] = "application/json"
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, data=encoded, headers=request_headers, method=method),
            timeout=timeout,
        ) as response:
            raw = response.read()
            elapsed = (time.perf_counter() - started) * 1000
            text = raw.decode("utf-8")
            try:
                parsed: object = json.loads(text) if text else None
            except json.JSONDecodeError:
                parsed = text
            return Result(response.status, parsed, elapsed)
    except urllib.error.HTTPError as error:
        elapsed = (time.perf_counter() - started) * 1000
        raw = error.read()
        text = raw.decode("utf-8")
        try:
            parsed = json.loads(text) if text else None
        except json.JSONDecodeError:
            parsed = text
        return Result(error.code, parsed, elapsed)


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]


def latency_summary(results: list[Result], expected_status: int = 200, wall_ms: float | None = None) -> dict[str, object]:
    latencies = [result.elapsed_ms for result in results]
    errors = sum(result.status != expected_status for result in results)
    return {
        "count": len(results),
        "expected_status": expected_status,
        "errors": errors,
        "p50_ms": round(percentile(latencies, 0.50), 3),
        "p95_ms": round(percentile(latencies, 0.95), 3),
        "max_ms": round(max(latencies), 3),
        "throughput_rps": round(len(results) / ((wall_ms if wall_ms is not None else sum(latencies)) / 1000), 3),
    }


def dispatch_body(index: int, candidates: int = 1) -> dict[str, object]:
    return {
        "request_id": f"rm180-dispatch-{index}",
        "strategy": "risk-aware",
        "pickup": {"latitude": 31.2304, "longitude": 121.4737},
        "candidates": [
            {
                "courier_id": f"rm180-courier-{candidate}",
                "location": {"latitude": 31.2304, "longitude": 121.4737},
                "capacity_units": 4,
                "service_risk": 0.1,
                "overtime_risk": 0.1,
            }
            for candidate in range(candidates)
        ],
    }


def run_dispatch() -> dict[str, object]:
    total = 128
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = [
            pool.submit(request, "POST", f"{COMPUTE}/api/v1/dispatch/snapshot", dispatch_body(index))
            for index in range(total)
        ]
        results = [future.result() for future in futures]
    wall_ms = (time.perf_counter() - started) * 1000
    summary = latency_summary(results, wall_ms=wall_ms)
    if summary["errors"] != 0:
        raise AssertionError(f"dispatch errors: {summary}")
    if summary["p95_ms"] > 2000:
        raise AssertionError(f"dispatch p95 exceeded local bound: {summary}")
    bound = request("POST", f"{COMPUTE}/api/v1/dispatch/snapshot", dispatch_body(999, 65))
    if bound.status != 422:
        raise AssertionError(f"dispatch candidate bound expected 422, got {bound.status}")
    summary["candidate_bound_status"] = bound.status
    print(f"PASS: dispatch {json.dumps(summary, sort_keys=True)}")
    return summary


def run_twin() -> dict[str, object]:
    reset = request("POST", f"{COMPUTE}/api/v1/twin/control", {"command_id": "rm180-reset", "action": "reset"})
    if reset.status != 200:
        raise AssertionError(f"twin reset failed: {reset.status}")
    results: list[Result] = []
    started = time.perf_counter()
    for index in range(64):
        results.append(request("POST", f"{COMPUTE}/api/v1/twin/control", {
            "command_id": f"rm180-step-{index}", "action": "step", "seconds": 1,
        }))
    wall_ms = (time.perf_counter() - started) * 1000
    summary = latency_summary(results, wall_ms=wall_ms)
    final_state = results[-1].body["state"] if isinstance(results[-1].body, dict) else {}
    if summary["errors"] != 0 or final_state.get("simulated_time_seconds", 0) < 64:
        raise AssertionError(f"twin tick gate failed: {summary}, state={final_state}")
    replay_body = {"command_id": "rm180-replay", "action": "speed", "speed": 1.0}
    first = request("POST", f"{COMPUTE}/api/v1/twin/control", replay_body)
    second = request("POST", f"{COMPUTE}/api/v1/twin/control", replay_body)
    if first.status != 200 or second.status != 200 or not second.body.get("replayed", False):
        raise AssertionError("twin command replay was not idempotent")
    summary["simulated_time_seconds"] = final_state["simulated_time_seconds"]
    summary["scenario_tick"] = final_state["tick"]
    summary["event_count"] = final_state["event_count"]
    summary["replay"] = True
    print(f"PASS: twin {json.dumps(summary, sort_keys=True)}")
    return summary


def create_order(index: int) -> Result:
    order_key = str(uuid5(NAMESPACE_URL, f"routemind-rm180-order-{SEED}-{index}"))
    return request("POST", f"{BUSINESS}/api/v1/orders", {}, {
        "Idempotency-Key": order_key, "X-Actor": "customer",
    })


def run_sse() -> dict[str, object]:
    total = 80
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(create_order, range(total)))
    if any(result.status not in (200, 201) for result in results):
        raise AssertionError(f"order fanout failed: {[result.status for result in results if result.status not in (200, 201)]}")
    started = time.perf_counter()
    stream = request("GET", f"{BUSINESS}/api/v1/events/stream?after=0", timeout=15)
    stream_elapsed = (time.perf_counter() - started) * 1000
    if stream.status != 200 or not isinstance(stream.body, str):
        raise AssertionError(f"SSE stream failed: {stream.status}")
    cursors = [int(value) for value in re.findall(r"^id:\s*(\d+)\s*$", stream.body, re.MULTILINE)]
    if not cursors or cursors != sorted(set(cursors)):
        raise AssertionError("SSE cursors are missing or not strictly ordered")
    if len(cursors) > 64:
        raise AssertionError(f"SSE batch bound exceeded: {len(cursors)}")
    stale = request("GET", f"{BUSINESS}/api/v1/events/stream?after=1")
    if stale.status != 409:
        raise AssertionError(f"stale SSE cursor expected 409, got {stale.status}")
    metrics = request("GET", f"{BUSINESS}/metrics")
    if metrics.status != 200:
        raise AssertionError(f"Java metrics endpoint failed: {metrics.status}")
    summary = {
        "created_events": total,
        "stream_events": len(cursors),
        "first_cursor": cursors[0],
        "last_cursor": cursors[-1],
        "stream_latency_ms": round(stream_elapsed, 3),
        "batch_bound": 64,
        "stale_cursor_status": stale.status,
        "metrics_status": metrics.status,
    }
    print(f"PASS: sse {json.dumps(summary, sort_keys=True)}")
    return summary


def main() -> int:
    result: dict[str, object] = {
        "schema_version": "v1",
        "seed": SEED,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "configuration": {
            "dispatch_requests": 128,
            "dispatch_concurrency": 8,
            "twin_steps": 64,
            "sse_created_events": 80,
            "sse_batch_limit": 64,
        },
    }
    result["dispatch"] = run_dispatch()
    result["twin"] = run_twin()
    result["sse"] = run_sse()
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":"))
    result["result_digest"] = hashlib.sha256(canonical.encode()).hexdigest()
    print("RESULT_JSON=" + json.dumps(result, sort_keys=True))
    print("RESULT_DIGEST=" + result["result_digest"])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"FAIL: performance/realtime gate: {error}", file=sys.stderr)
        raise
