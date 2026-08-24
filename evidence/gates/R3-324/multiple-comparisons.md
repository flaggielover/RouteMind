# R3-324 multiple-comparison control evidence

Date: 2026-08-24 (Asia/Shanghai)

Base revision: `a8bc847f332aec8e1f16441c12da099c242dc5cd` plus the R3-324
implementation worktree

## Frozen scope

R3-324 implements the R3-320 preregistered
`holm_bonferroni_familywise` method over exactly 16 directional hypotheses:
eight regime-specific risk-superiority tests and eight regime-specific
assignment-noninferiority tests. The family order is metric then the frozen
regime order. Input order cannot change a report.

Each input and output retains protocol, regime, metric, and canonical hypothesis
identity. Reports retain the raw p-value, stable family rank, Holm multiplier,
sequential alpha threshold, monotonic adjusted p-value, rejection decision,
family disposition, and content digest. Equal raw p-values use frozen family
order only for deterministic ranking; their adjusted values remain equal.

The standard Holm calculation sorts ascending raw p-values, multiplies rank `i`
by `m-i+1`, applies a cumulative maximum, and caps adjusted p-values at one.
Results are returned in frozen family order. Every one of the 16 adjusted tests
must reject at familywise alpha 0.05 for the family disposition to pass. This
engineering result is not itself observed statistical evidence or an effect
claim.

## Validation vectors

For ordered raw p-values `0.001, 0.002, 0.003, 0.004`, followed by twelve
values of `1.0`, the first four Holm adjusted values are `0.016, 0.030, 0.042,
0.052`; their decisions are reject, reject, reject, retain. The report rejects
3 of 16 hypotheses and has digest
`53580e4f07ce361b12cad87a3f2e81f086a5f93de5fbfab16563ac0679e3e18c`.

Sixteen tied raw values of `0.003125` each adjust to the exact family boundary
`0.05`; frozen family order determines ranks while every tied value receives
the same adjusted value. Reversing the input sequence preserves the report and
digest. Invalid p-values, protocol identity drift, duplicate/missing identities,
method/family/count/alpha drift, and a forged duplicate regime fail closed.

## Executed gates

- Isolated multiplicity branch gate: PASS, 22/22; 108 statements and 28 branches
  at 100% coverage. The precise command clears the repository-wide pytest
  coverage defaults before selecting only the target module.
- Protocol/estimation/power/multiplicity integration: PASS, 143/143.
- Ruff and strict mypy over all compute source/tests: PASS; 115 source files
  type checked by the full gate.
- `routebench-multiplicity` is registered `DETERMINISM_CRITICAL`; protocol
  loading now retains the frozen multiplicity method and family description.
- `./scripts/full-gate.ps1`: PASS at 2026-08-24T19:03+08:00. Java 81/81;
  Python 657/657 at 95.88% total coverage; Web 34 files / 92 tests plus
  production build; 6 schemas / 18 fixtures; controls, dependency lock,
  determinism, analytics, and semantic metrics passed.

The first final-gate attempt exposed an existing Java clock-granularity defect:
an order transition could observe the same instant as order creation and violate
the domain's strict timestamp ordering. The failure was diagnosed from the
Surefire request trace, reproduced with a fixed clock, and repaired by advancing
transition time by one nanosecond when the application clock has not advanced.
The outbox event now uses the saved aggregate time. The fixed-clock regression,
the originally failing lease test, and the complete 81-test Java suite pass.

Implementation revision `c3e394b` passed all five GitHub Actions jobs in run
`32720233681`, including frozen Python/contracts, Java, resilience, and browser
smoke.

Final disposition: `E-PASS / X-NOT-REQUIRED / S-NOT-APPLICABLE /
C-NOT-APPLICABLE`. No pilot, confirmatory campaign, observed p-value,
statistical effect, or strategy claim was produced.
