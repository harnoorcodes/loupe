# Ablation study

Each configuration removes one component and re-scores against the
same corpus. The difference from the baseline is what that component
contributes.

| Configuration | Recall | Noise | Proposed | Confirmed | vs baseline |
| --- | --- | --- | --- | --- | --- |
| full | 7/15 (47%) | 0/8 (0%) | 16 | 8 | baseline |
| no pair detector | 3/15 (20%) | 0/4 (0%) | 5 | 4 | -4 defects |
| no tension detector | 7/15 (47%) | 0/8 (0%) | 14 | 8 | no change |
| no entity resolution | 6/15 (40%) | 0/7 (0%) | 15 | 7 | -1 defects |
| no adversarial review | 8/15 (53%) | 7/16 (44%) | 16 | 16 | +1 defects |
| deterministic only | 2/15 (13%) | 0/3 (0%) | 3 | 3 | -5 defects |

## What each configuration tests

- **full** — Every component enabled. The baseline.
- **no pair detector** — Targeted pair analysis removed; entity-grouped tension only.
- **no tension detector** — Entity-grouped analysis removed; targeted pairs only.
- **no entity resolution** — Name variants no longer merged, so claims group by raw subject.
- **no adversarial review** — Findings reported without being challenged.
- **deterministic only** — No model calls at all. Arithmetic, dates and gap audit only.

## Which defects each configuration finds

| Defect | full | no pair detector | no tension detector | no entity resolution | no adversarial review | deterministic only |
| --- | --- | --- | --- | --- | --- | --- |
| D-001 | yes | yes | yes | yes | yes | yes |
| D-004 | - | - | - | - | - | - |
| D-005 | - | - | - | - | - | - |
| D-006 | yes | yes | yes | yes | yes | - |
| D-007 | yes | - | yes | - | yes | - |
| D-008 | - | - | - | - | yes | - |
| D-002 | yes | - | yes | yes | yes | - |
| D-009 | - | - | - | - | - | - |
| D-010 | - | - | - | - | - | - |
| D-003 | yes | yes | yes | yes | yes | yes |
| D-011 | - | - | - | - | - | - |
| D-012 | - | - | - | - | - | - |
| D-013 | - | - | - | - | - | - |
| D-014 | yes | - | yes | yes | yes | - |
| D-015 | yes | - | yes | yes | yes | - |
