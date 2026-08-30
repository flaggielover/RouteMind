# Simple Explanation Attack

Each candidate was required to reproduce across multiple seeds before attack.

- **AD-001**: Explained: the frozen runner instantiates ScenarioKernel(strategy=nearest) and does not perform policy selection. Verdict: `EXPLAINED`.
- **AD-002**: Measurement artifact: provider fallback is exercised by the travel layer but ScenarioKernel does not copy TravelTime.fallback_used into PolicyObservation.fallback_state. Verdict: `MEASUREMENT_ARTIFACT`.

No candidate survived the predefined simple explanation checks. Missing fallback state is retained as an instrumentation limitation and is not imputed or promoted to a runtime instability claim.
