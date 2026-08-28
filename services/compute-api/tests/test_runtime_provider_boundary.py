from routemind_compute.api.runtime import create_runtime
from routemind_compute.application.travel import (
    FallbackTravelTimeProvider,
    TracedTravelTimeProvider,
)


def test_runtime_selects_google_primary_and_local_fallback_without_live_io() -> None:
    runtime = create_runtime()
    assert isinstance(runtime.travel_provider, TracedTravelTimeProvider)
    traced = runtime.travel_provider
    delegate = traced.delegate
    assert isinstance(delegate, FallbackTravelTimeProvider)
    assert delegate.primary.name == "google-routes"
    assert delegate.fallback.name == "deterministic-local"
