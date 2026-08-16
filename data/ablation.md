# Ablation study

Each configuration removes one component and re-scores against the
same corpus. The difference from the baseline is what that component
contributes.

| Configuration | Recall | Noise | Proposed | Confirmed | vs baseline |
| --- | --- | --- | --- | --- | --- |
| full | 8/15 (53%) | 0/9 (0%) | 18 | 9 | baseline |
| no pair detector | 5/15 (33%) | 0/6 (0%) | 7 | 6 | -3 defects |
| no tension detector | 8/15 (53%) | 0/9 (0%) | 16 | 9 | no change |
| no entity resolution | 7/15 (47%) | 0/8 (0%) | 17 | 8 | -1 defects |
| no adversarial review | 10/15 (67%) | 7/18 (39%) | 18 | 18 | +2 defects |
| deterministic only | 4/15 (27%) | 0/5 (0%) | 5 | 5 | -4 defects |

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
| D-002 | - | - | yes | - | yes | - |
| D-009 | - | - | - | - | - | - |
| D-010 | - | - | - | - | - | - |
| D-003 | yes | yes | yes | yes | yes | yes |
| D-011 | yes | yes | - | yes | yes | yes |
| D-012 | yes | yes | yes | yes | yes | yes |
| D-013 | - | - | - | - | - | - |
| D-014 | yes | - | yes | yes | yes | - |
| D-015 | yes | - | yes | yes | yes | - |
