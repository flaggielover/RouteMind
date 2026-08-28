# ADR-0036: Google Routes replacement-provider gate

Date: 2026-08-28  
Status: Accepted for preparation only

## Context

HERE Matrix Routing API v8 Japan entitlement remains unconfirmed under frozen
R4-411 evidence. Google Maps Platform Routes API is an independent alternative
candidate, but no Google live call is authorized in this preparation pass.

The audited Round 4 graph has a fixed 38-task inventory and strict mirror gate.
Adding a new task ID would change the denominator and critical-spine contract and
would falsely imply that a replacement provider changes the original HERE task's
dependency semantics.

## Decision

Represent R4-411B as an independent replacement-provider gate attached to R4-411's
evidence/control-plane record. The canonical R4-411 task remains blocked and its
HERE contract, evidence, digest, and status remain immutable. R4-411B has its own
contract, digest, evidence, zero-live-call claim boundary, and future Human Gate.

This preserves the 38-task denominator while making the alternative provider
auditable and preventing provider-neutral preparation from being counted as live
validation or production readiness. The Google adapter uses the existing
provider-neutral `TravelTimeProvider` seam and deterministic-local fallback.

## Consequences

Google Routes can be evaluated independently after a new exact Human Gate and
bounded execution approval. Google-managed processing is not claimed Tokyo-pinned;
point Japan support and Matrix entitlement remain separate claims. No API key value,
account identifier, business identifier, or provider response is persisted in Git,
logs, evidence, or frontend artifacts. R4-411/HERE, R4-405/R4-406, and frozen
R3-325 outcomes are unchanged.
