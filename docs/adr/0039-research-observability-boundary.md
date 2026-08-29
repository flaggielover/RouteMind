# ADR 0039: Future Research Observability Boundary

Date: 2026-08-29
Status: Accepted for RM-237

## Context

The frozen R3-325 result lacks historical tick-level policy-switch evidence.
Future research needs a reproducible observation contract, but the missing
history cannot be reconstructed and the result must not be reopened.

## Decision

Add a small cross-runtime observation layer. Java extends the durable dispatch
decision ledger and transactional provenance with versioned metadata. Python
records aligned policy observations, switch metrics, replay digests, and a
privacy-bounded JSONL projection below `ROUTEMIND_DATA_ROOT`. Consequence
components retain explicit measurement status rather than being collapsed into
an invented scalar or causal claim.

The existing dispatch state machine, solver decisions, Outbox semantics, and
provider/Human Gate boundaries remain authoritative. Observation metadata is
optional-compatible for existing command callers and is included in the
ledger idempotency fingerprint so a replay cannot silently change context.

## Consequences

Future runs can answer when and why a policy switched and reconstruct the
deterministic decision sequence. Real-world frequency, realized cost, causal
effects, historical backfill, and production validity remain outside this
checkpoint and require new evidence and authorization.
