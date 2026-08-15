# Evaluation

**Project:** Loupe — a multi-agent due diligence system for M&A data rooms

---

## 1. Why the benchmark exists

Most systems in this space cannot tell you whether their output is correct. An agent reads documents, produces findings, and the findings sound plausible. Nobody — including the person who built it — can say what it missed.

That is not a measurement problem that better prompting solves. It is a ground-truth problem. Without knowing what is actually wrong with a corpus, recall is unknowable.

Loupe therefore generates its own corpus. Thirty-five documents describing a fictional company, with fifteen defects planted at known locations across six classes. Because the corpus is written rather than collected, ground truth is exact: every defect's location, type, and the capability its detection requires are all recorded.

This makes three things possible that are otherwise not:

- **Recall is measured**, not asserted.
- **Per-class results** show which kinds of problem the system finds and which it does not.
- **Ablation** is meaningful, because removing a component and re-scoring compares against a fixed target.

---

## 2. Benchmark design

### 2.1 The corpus

Thirty-five documents for Northwind Analytics Inc., a fictional B2B SaaS company being acquired.

| Category | Documents |
| --- | --- |
| Corporate | 8 — charter, bylaws, cap table, three sets of board minutes, shareholders agreement, share ledger |
| Financial | 7 — two years of statements, revenue by customer, deferred revenue, receivables ageing, loan agreement, management accounts |
| Commercial | 8 — four customer contracts, two amendments, a reseller agreement, a supplier agreement |
| Employment | 6 — three executive agreements, option grant schedule, contractor agreement, severance policy |
| Compliance | 6 — IP assignment, insurance, trademark, litigation summary, data processing agreement, vendor list |

Documents are rendered to PDF and DOCX so that the ingestion pipeline is exercised end to end, including the offset preservation that citations depend on.

### 2.2 The defects

Fifteen defects across six classes, each recorded with the capability its detection requires.

| Class | Count |
| --- | --- |
| Arithmetic | 3 |
| Cross-document contradiction | 3 |
| Latent liability | 3 |
| Missing document | 2 |
| Temporal impossibility | 2 |
| Undisclosed relationship | 2 |

By difficulty: **3 easy, 8 medium, 4 hard**.

The four hard defects were designed to exceed the implementation at the time the corpus was written:

| Defect | Requires |
| --- | --- |
| D-008 | Version handling: knowing an amendment supersedes a term |
| D-010 | A three-document chain plus geographic inference |
| D-013 | Inference from a delivery date to an assignment date |
| D-015 | Coreference across an abbreviated name and a shared address |

Including defects the system is expected to fail is deliberate. A benchmark that scores 100% on its first run is measuring the benchmark rather than the system, and provides no signal about where to work next.

### 2.3 Consistency verification

A planted defect that is not really there scores as a permanent miss and would quietly cap the benchmark. Before generation, a verifier checks that:

- every document a defect names exists
- at least one anchor phrase for each defect appears in the documents it names
- the arithmetic behind each numeric defect works out
- shared addresses appear in the documents the relationship defects depend on

```bash
python scripts/generate_corpus.py --verify
```

This caught two real errors during construction: two anchors referenced values the system *calculates* rather than values appearing in any document, which would have made those defects undetectable by the scoring rules.

### 2.4 Scoring rules

A finding detects a defect when both hold:

1. The finding's type is one the defect accepts. Several types may be accepted, because one real problem can be correctly classified in more than one way — a change-of-control exposure is both a cross-document contradiction and a latent liability, and insisting on a single label would score a correct answer as a miss.
2. At least one of the defect's anchor phrases appears somewhere in the finding's title, description, or cited spans. Only one anchor is required, because a finding may quote a narrower span than the sentence the defect lives in.

Each finding can claim at most one defect, so a single finding cannot inflate the score.

Leftover findings are split rather than lumped together:

- **Genuine absences that were never planted.** The corpus contains no tax returns, so reporting them missing is correct behaviour and is counted separately.
- **Findings corresponding to nothing real.** These are the noise rate.

Counting a correct-but-unplanted finding as an error would understate the system; counting it as a success would overstate it.

---

## 3. Results

```bash
python -m loupe.cli score
```

| | |
| --- | --- |
| **Overall recall** | 7 / 15 (47%) |
| **Noise rate** | 0 / 8 (0%) |
| **Claims extracted** | 232 from 35 documents |

### 3.1 By defect class

| Class | Found | Planted | Recall |
| --- | --- | --- | --- |
| Undisclosed relationship | 2 | 2 | 100% |
| Missing document | 1 | 2 | 50% |
| Arithmetic | 1 | 3 | 33% |
| Cross-document contradiction | 1 | 3 | 33% |
| Latent liability | 1 | 3 | 33% |
| Temporal impossibility | 0 | 2 | 0% |

### 3.2 By difficulty

| Difficulty | Found | Planted | Recall |
| --- | --- | --- | --- |
| Easy | 3 | 3 | 100% |
| Medium | 2 | 8 | 25% |
| Hard | 2 | 4 | 50% |

Hard outscoring medium is not an error. The two hard defects that were caught — D-013 and D-015 — both turned on a shared street address, which the candidate pair generator matches literally. The capability I predicted they would need (coreference resolution, temporal inference) turned out not to be the only route to them. That is a result worth reporting precisely because it contradicts the prediction recorded in the corpus.

### 3.3 Every defect

| Defect | Difficulty | Requires | Found |
| --- | --- | --- | --- |
| D-001 Share total does not reconcile | easy | arithmetic reconciliation | yes |
| D-002 Change of control right held by largest customer | easy | cross-document reasoning | yes |
| D-003 Equity incentive plan referenced but absent | easy | negative space audit | yes |
| D-004 Option grants exceed the cap table figure | medium | cross-document arithmetic | no |
| D-005 Revenue schedule exceeds stated total revenue | medium | cross-document arithmetic | no |
| D-006 CFO salary contradicts the board resolution | medium | cross-document comparison | yes |
| D-007 Deferred revenue stated differently in two documents | medium | cross-document comparison | yes |
| D-009 Loan acceleration exceeds available cash | medium | cross-document reasoning | no |
| D-011 Board consent for CFO appointment absent | medium | reference-driven gap audit | no |
| D-012 Amendment dated before the amendment it amends | medium | date ordering across documents | no |
| D-014 Supplier shares an address with the CEO | medium | address matching across documents | yes |
| D-008 Revenue recognised on a superseded fee | hard | version handling | no |
| D-010 Direct sale into an exclusive reseller territory | hard | three-document chain, geographic inference | no |
| D-013 Contractor IP created before its assignment took effect | hard | delivery-to-assignment inference | yes |
| D-015 Contractor connected to the CTO | hard | coreference and shared address | yes |

---

## 4. Ablation study

```bash
python -m loupe.cli ablate
```

Each configuration removes one component and re-scores against the same corpus. Most configurations are subsets of the full pipeline, so their model calls are already in the response cache and re-running costs nothing.

| Configuration | Recall | Noise | Proposed | Confirmed | vs baseline |
| --- | --- | --- | --- | --- | --- |
| Full system | 7/15 (47%) | 0/8 (0%) | 16 | 8 | baseline |
| No pair detector | 3/15 (20%) | 0/4 (0%) | 5 | 4 | −4 defects |
| No tension detector | 7/15 (47%) | 0/8 (0%) | 14 | 8 | no change |
| No entity resolution | 6/15 (40%) | 0/7 (0%) | 15 | 7 | −1 defect |
| No adversarial review | 8/15 (53%) | 7/16 (44%) | 16 | 16 | +1 defect, +7 noise |
| Deterministic only | 2/15 (13%) | 0/3 (0%) | 3 | 3 | −5 defects |

### 4.1 The critic trades recall for precision

The most useful number in the study.

Disabling adversarial review raises recall from 7/15 to 8/15 — it recovers D-008, the superseded-fee finding — and simultaneously raises the noise rate from 0% to 44%. Sixteen findings are reported instead of eight, and seven of the additional ones correspond to nothing real.

This is the precision–recall tradeoff with a number attached rather than an opinion. It also identifies a specific over-aggression: the critic dismisses D-008 as "a standard contractual progression," which is a defensible reading and a wrong one.

For a diligence report, precision is the more valuable side of that trade. An analyst who encounters seven false findings stops reading, at which point effective recall is zero regardless of what was measured.

### 4.2 The pair detector accounts for most of the recall

Removing targeted pair analysis drops recall from 7 to 3. Every undisclosed-relationship defect, the deferred-revenue contradiction, and the change-of-control liability are lost.

This validates the design decision described in the multi-agent document: separating *which claims to compare* (deterministic, exhaustive, free) from *whether a comparison is a finding* (model, narrow question).

### 4.3 The tension detector contributes nothing

Removing it changes no result. On this corpus it finds only what the pair generator already finds.

This is reported rather than hidden because it is the kind of result a component's author is least inclined to look for. The component remains in the system because it is the more general mechanism — it can surface conflict shapes no rule anticipates — but it currently earns no cost, and that is the honest reading.

### 4.4 The model earns its cost

Deterministic detectors alone reach 2/15. The full system reaches 7/15. Whatever else is true, the language model is doing work that rules do not.

Equally: two defects need no model at all, which is why half the components are deterministic.

---

## 5. Threats to validity

**The corpus is synthetic and written by the same author as the system.** Both the defects and the detectors reflect one person's model of what goes wrong in a data room. A defect nobody thought to plant cannot be missed, and cannot be measured.

**Thirty-five documents is small.** A real mid-market data room holds several hundred. Gap detection in particular is much easier at this scale, which is why the 0% noise rate should not be read as a strong claim.

**Single deal archetype.** Everything is tuned for a B2B SaaS acquisition in the USD 5–50M range.

**Output is not deterministic without the cache.** The same inputs produced 6/15 on one run and 7/15 on another, differing on a single uncached critic call. The reported figure is from a cached run, which is reproducible; a cold run may vary by one defect.

**Anchor-based scoring is approximate.** A finding matches a defect if one anchor phrase appears anywhere in it. A finding that mentions the right number for the wrong reason would score as a detection. Manual inspection of the seven detections found no such case, but the rule permits it.

---

## 6. What the results say to do next

The per-defect table is a prioritised backlog derived from measurement rather than guesswork.

| Work | Recovers | Evidence |
| --- | --- | --- |
| Fix component selection in total-versus-parts pairs | D-004, D-005 | Both pairs were generated; the arithmetic in their reason strings was contaminated by figures from other periods, so the adjudicator correctly rejected them |
| Soften the critic on amendment-driven changes | D-008 | The no-review ablation recovers it |
| Debug the amendment-ordering check | D-012 | The check runs and never fires |
| Reference-driven gap detection | D-011 | No detector exists for a document referenced by another document |
| Pair generation for the loan-versus-cash shape | D-009 | No candidate pair was produced |
| Version handling | D-008, and false positives on any real corpus | Amendments are currently treated as contradictions |

Two of these — reference-driven gap detection and version handling — are capabilities most systems in this space do not have, rather than bug fixes.
