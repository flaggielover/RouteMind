# RM-060 Role-Aware Web Application Design

## Context

RouteMind needs its first product surface without duplicating applications for
operations, strategy, customer, merchant, and courier roles. The durable Java
runtime currently exposes health and system identity endpoints but not a public
order-query API. The Python runtime exposes health and system identity endpoints
while dispatch and simulation capabilities remain framework-level modules.

The first web increment must therefore make the end-to-end delivery lifecycle
visible without pretending that fixture data is live business state. It must also
create a maintainable boundary for later API and real-time integrations.

## Decision

Create one React and TypeScript application under `apps/web`. A shared application
shell owns navigation, role context, responsive layout, service status, and common
visual language. Each role surface consumes a typed operations snapshot through a
data-source interface rather than importing UI-specific fixture objects.

RM-060 ships a deterministic `demo` data source that is visibly identified in the
interface. It represents one complete order lifecycle, active courier supply,
merchant preparation, a dispatch decision, and current operational exceptions.
Service health uses a separate adapter with configurable Java and Python base URLs;
an unavailable or cross-origin endpoint is rendered as `unavailable`, never as a
successful live connection.

The application uses route paths for `operations`, `strategy`, `customer`,
`merchant`, and `courier`. These are role views over shared state, not independently
deployed applications. Route configuration and role metadata remain centralized.

## Alternatives Considered

### Separate role applications

Separate builds provide strong deployment isolation but would duplicate navigation,
tokens, data access, testing, and release configuration before any deployment or
scaling requirement justifies that cost.

### Static single dashboard

A static dashboard is smaller initially, but role switching, deep links, data-source
replacement, and end-to-end testability would become implicit UI state. That would
make the next product-surface increment harder to maintain.

### Shared role-aware application

The selected approach has one build and one component foundation while preserving
clear role routes and data contracts. It matches the modular-monorepo architecture
and is the smallest structure that supports all RM-060 acceptance criteria.

## User Experience

The default route is the operations command screen. A compact left navigation rail
switches roles on desktop and becomes a top tab strip on smaller screens. The main
surface prioritizes scan speed:

- a restrained status header with data-source and service health;
- operational metrics for active orders, available couriers, assignment latency,
  and exceptions;
- a city dispatch map with merchant, courier, customer, and route state;
- an order queue and lifecycle timeline that expose the complete flow;
- focused strategy, customer, merchant, and courier views using the same snapshot.

Controls use familiar Lucide icons with accessible names and tooltips. Status never
depends on color alone. The palette combines neutral surfaces with green, amber,
red, cyan, and blue semantic signals rather than a single dominant hue.

## Components and Boundaries

- `app`: route composition, application shell, navigation, and error boundary.
- `domain`: typed role, order, courier, merchant, dispatch, and service-health
  models with small derived selectors.
- `data`: `OperationsDataSource` and service-health adapters. The demo snapshot is
  immutable and deterministic.
- `features`: operations, strategy, customer, merchant, and courier views. Feature
  modules consume domain selectors and shared presentation components.
- `components`: status indicators, metric cells, lifecycle timeline, map legend,
  and accessible icon controls.

No browser module writes durable business state. Later command flows must call Java
business APIs or a justified BFF; the frontend will not become a second owner of
order lifecycle correctness.

## Data Flow and Failure Handling

On startup, the selected data source returns the deterministic operations snapshot.
The app derives role-specific views from that snapshot without mutation. Health
probes run independently and settle as `healthy`, `unavailable`, or `checking`.
Probe timeouts, network failures, malformed responses, and absent configuration are
handled as explicit unavailable states and do not prevent the demo workflow from
rendering.

An application error boundary provides a compact recovery action for unexpected
rendering failures. Empty collections have intentional empty states. Responsive
layouts use bounded grid tracks and overflow-safe controls so content does not
overlap from mobile through wide desktop viewports.

## Verification

The web gate is a repository PowerShell entry point and runs:

1. formatting verification, ESLint, and TypeScript type checking;
2. Vitest unit/component tests for selectors, role navigation, lifecycle visibility,
   source labeling, and failure states;
3. a production Vite build;
4. Playwright browser smoke tests at desktop and mobile viewports;
5. axe accessibility checks for each primary role route.

Playwright verifies that all role routes render, the full order lifecycle remains
visible, mobile navigation is usable, and no horizontal document overflow occurs.
The GitHub Actions workflow installs a pinned Node runtime and Chromium before
running the same web gate. Evidence records local and CI results separately.

## Scope Boundaries

RM-060 does not add authentication, authorization, WebSocket delivery, a BFF,
state-changing business commands, or new Java/Python business endpoints. It creates
the product-surface foundation and truthful local browser evidence. Live order data,
command authorization, and real-time subscriptions require later contracts and
tasks.
