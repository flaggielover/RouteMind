# P2 Redis GEO Courier Projection

Courier location writes first pass through a durable `CourierLocationStore`.
Redis GEO is a rebuildable read projection keyed by courier ID; it is never the
authoritative location record.

The application service reports `PROJECTED` when Redis accepts the update and
`DEGRADED` when the durable write succeeds but Redis is unavailable. Nearby
queries return projection results and expose the same degraded state so callers
can choose a fallback. A rebuild operation clears and repopulates the GEO key
from durable locations.
