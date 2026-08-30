# RouteMind Operations Visual Correction Design

## Objective

Correct the approved seven-chapter Operations experience without adding new visual
features. The order of work is semantic clarity, layout integrity, composition,
inspection interaction, then decorative polish.

## Spatial grammar

The persistent WebGL world will lead with an urban logistics field rather than a
central abstract object. Snapshot-derived district clusters contain demand cells;
orders, couriers, merchants, and risk incidents use distinct node geometry;
directional route markers expose movement; and bounded district surfaces expose SLA
risk. A smaller strategy anchor remains as one mapped operational entity and no
longer dominates the scene. Visible labels and the legend name this grammar.

`UrbanFieldState.spatial.zones` gains optional renderer-neutral labels and bounded
pressure, supply, and selection values. This remains deterministic visual projection
data and does not claim production H3 or calibrated Digital Twin state.

## Layout correction

The Live Operations top composition will stop overlapping Multi-city and City/Zone
surfaces. Panels receive shrink-safe grid/flex boundaries. The City/Zone table uses a
compact fixed layout where it has room and a labelled row composition where it does
not; horizontal scrolling is not the default fallback. Headings, tabs, legends,
metadata, and controls wrap at their semantic boundaries.

## Inspection interaction

The global cursor decoration is removed and the native cursor remains. Scene
inspection is expressed through raycast focus, nearby cell response, restrained
local lens clarity, and selected-entity text. Chart and HUD surfaces use a small
local focus response. RGB separation is zero at rest and limited to an intentional
pressed inspection beat.

## Verification

Browser gates cover 1280x720, 1024x768, and 760x800 in normal motion, plus a static
reduced-motion pass. Each gate checks document and primary-panel overflow, label and
control containment, panel collision, spatial meaning, canvas pixels, pointer
behavior, and console output. Focused tests, lint, typecheck, build, and the risk-based
web suite must pass before RM-243 is marked passed.
