# RM-231 Research Center Evidence

Date: 2026-08-24  
Status: passed

## Scope

- Added a lineage-first Research Center to the Strategy surface.
- Experiment manifest fields include manifest ID, scenario, seed, code version,
  reference-data identity, and strategy versions.
- Existing recorded comparisons become engineering observations with replay,
  manifest, output, and comparison digest references.
- Missing comparison data remains fixture/pending; scientific claims and deep
  research campaigns are explicitly deferred.

## Local evidence

- `./scripts/web.ps1 check`: PASS - 34 test files, 92 unit tests, Prettier,
  ESLint, TypeScript, and Vite production build.
- `./scripts/web.ps1 e2e`: PASS - 34 Playwright tests, 2 existing desktop-only
  skips. Strategy, What-if, role, mobile, and accessibility flows remain green.
- Focused projection and panel tests cover ready comparisons, artifact lineage,
  fixture/pending state, and the scientific-claim boundary.

## Remote evidence

Checkpoint: pending

GitHub Actions: pending checkpoint push.

## Boundaries

The panel does not launch experiments, mutate artifacts, rank production
strategies, or assert scientific novelty. Compute and external data roots remain
the source of analytical artifacts and durable provenance.
