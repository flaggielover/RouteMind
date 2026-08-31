# RouteMind Web

The role-aware product surface shares one React/TypeScript shell across
operations, strategy, customer, merchant, and courier routes. The current
`demo` data source is deterministic so browser and unit evidence can be repeated
without inventing a public order-query API. Service health probes remain
separate and report `healthy`, `checking`, or `unavailable` explicitly.

From `apps/web`:

```powershell
npm install
npm run dev
npm run check
npm exec playwright install chromium
npm run test:e2e
```

The production surface is intentionally not an owner of durable business state.
Future command flows must call the Java business API or an explicitly justified
BFF, while Python remains the owner of dispatch and simulation computation.

## Operations basemap

Operations uses MapLibre with the complete OpenFreeMap Liberty vector style by
default. The style is backed by OpenStreetMap data in the OpenMapTiles schema and
requires the attribution rendered by the map source. The default provider does not
require an API key; its public instance does not provide an application SLA.

An explicitly configured MapLibre style can be supplied without changing Deck.gl
operational layers:

```text
VITE_MAP_STYLE_URL=https://provider.example/styles/operations
VITE_MAP_PROVIDER_LABEL=Example Maps
VITE_MAP_ATTRIBUTION=Example Maps attribution
```

Configured providers retain their own style instead of receiving the RouteMind
OpenFreeMap theme transform. Their source style or `VITE_MAP_ATTRIBUTION` must carry
the provider's legally required attribution.
