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
