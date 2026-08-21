# P1 Identity and Party Model

## Scope

RM-010 introduces durable customer, merchant, and courier identities. It does
not introduce authentication, authorization, order state, courier location, or
cross-service events.

## Domain

`PartyIdentity` is a sealed, framework-free contract implemented by explicit
`CustomerIdentity`, `MerchantIdentity`, and `CourierIdentity` records. Every
identity has a UUID `PartyId`, a role-scoped external reference, and a display
name. External references are 1-64 visible identifier characters; display names
are trimmed, 1-120 characters, and reject control characters.

`Party` combines one identity with status and immutable `AuditMetadata`.
Creation records one timestamp for both creation and update. Domain changes must
retain creation time and advance update time. Persistence optimistic versioning
is adapter metadata and does not leak into the domain model.

## Persistence

One `routemind.parties` table stores the shared lifecycle and discriminates the
three roles with `party_type`. `(party_type, external_reference)` is unique.
Database checks mirror role, status, text length, and audit ordering invariants.
The application owns a repository port; Spring Data and JPA remain replaceable
infrastructure details.

## Validation

Domain tests cover all identity variants, invalid text, audit ordering, and
rename behavior. Repository component tests cover round trips, all role
mappings, uniqueness, and retained audit metadata. A real PostgreSQL gate applies
Flyway V2 and proves constraints and persisted audit fields outside H2.
