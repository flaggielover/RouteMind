# RM-251 Visual Material System Implementation Plan

## Objective

Implement the approved Frosted Atlas material direction in the existing React 19
Operations experience without changing data, map, courier, replay, research, or
locale contracts.

## Sequence

1. **Token audit and foundation**
   - Inventory current global colors, borders, radii, shadows, uppercase labels,
     and motion selectors in `apps/web/src/styles.css`.
   - Add environment, glass, semantic accent, radius, depth, and motion tokens.
   - Add reusable material utility classes for surface, overlay, rail, dock,
     inspector, and metric roles with light frosted fill, blur, saturation,
     inner highlight, and restrained shadow.

2. **Atmosphere and chapter hooks**
   - Extend the existing Operations motion root with city and chapter data
     attributes/CSS variables for low-frequency ambient focal lighting.
   - Keep the persistent MapLibre/Deck.gl world dark and readable.
   - Add reduced-motion rules that freeze drift/interpolation while retaining
     the composition and Pointer Lens.

3. **Selective surface adoption**
   - Apply material roles to `AppShell`, `OperationsExperience`, analytical
     strips, detail inspectors, replay/simulation docks, strategy panels, and
     research/evidence surfaces.
   - Remove redundant rectangular borders where spacing, type, blur, or depth
     already communicate hierarchy.
   - Keep technical tables and critical controls more opaque and compact.

4. **Typography and semantic color cleanup**
   - Reduce unnecessary all-caps mono labels.
   - Separate demand, supply, risk, strategy, and brand activity colors.
   - Preserve bilingual labels and machine identifiers.

5. **Responsive and accessibility pass**
   - Add 1280x720, 1024x768, and 760x800 layout rules.
   - Increase surface opacity and reduce overlap at narrow widths.
   - Verify focus rings, contrast, keyboard controls, native cursor, and map
     readability.

6. **Browser visual gates**
   - Capture before/after screenshots at desktop, laptop, and narrow widths.
   - Inspect static motion-disabled rendering and compare against the approved A
     prototype.
   - Verify all routes in Chinese and English and exercise city switching,
     pointer-lens exclusion, and the first scroll sequence.

7. **Automated gates and checkpoint**
   - Run Prettier, ESLint, typecheck, unit tests, build, and relevant browser
     smoke tests.
   - Review `git diff --check`, preserve unrelated work, and create one coherent
     RM-251 commit only after visual and automated gates pass.

## Files expected to change

- `apps/web/src/styles.css`
- `apps/web/src/components/AppShell.tsx`
- `apps/web/src/components/OperationsExperience.tsx`
- `apps/web/src/components/OperationsMotionCoordinator.tsx`
- `apps/web/src/components/AnalyticalVisualizationFoundation.tsx`
- `apps/web/src/components/StrategyComparisonPanel.tsx`
- `apps/web/src/components/StrategyAnalyticsPanel.tsx`
- `apps/web/src/components/ResearchCenterPanel.tsx`
- `apps/web/src/components/ReplayPlaybackPanel.tsx`
- `apps/web/src/components/SimulationControlPanel.tsx`

Only files that need material adoption will be changed; no backend or data
contract changes are in scope.

## Evidence

Record the browser URL, selected prototype event, viewport screenshots, static
motion-disabled screenshot, bilingual spot checks, and automated command output
in the final checkpoint summary. Do not claim external Codrops assets or copied
artwork; only implementation patterns and visual mechanisms are adapted.
