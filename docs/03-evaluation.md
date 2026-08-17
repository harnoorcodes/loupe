# Evaluation

**Project:** Loupe — a multi-agent due diligence system for M&A data rooms

---

## 1. Why the benchmark exists

Most systems in this space cannot tell you whether their output is correct. An agent reads documents, produces findings, and the findings sound plausible. Nobody — including the person who built it — can say what it missed.

That is not a measurement problem better prompting solves. It is a ground-truth problem. Without knowing what is actually wrong with a corpus, recall is unknowable.

Loupe therefore generates its own corpus. Thirty-five documents describing a fictional company, with fifteen defects planted at known locations across six classes. Because the corpus is written rather than collected, ground truth is exact: every defect's location, type, and the capability its detection requires are recorded.

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

Documents are rendered to PDF and DOCX so the ingestion pipeline is exercised end to end, including the offset preservation that citations depend on.

### 2.2 The defects

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

Including defects the system is expected to fail is deliberate. A benchmark that scores 100% on its first run is measuring the benchmark rather than the system, and gives no signal about where to work next.

### 2.3 Consistency verification

A planted defect that is not really there scores as a permanent miss and would quietly cap the benchmark. Before generation, a verifier checks that every named document exists, that at least one anchor phrase for each defect appears in the documents it names, that the arithmetic behind each numeric defect works out, and that shared addresses appear where the relationship defects need them.

```bash
python scripts/generate_corpus.py --verify
```

This caught two real errors during construction: two anchors referenced values the system *calculates* rather than values appearing in any document, which would have made those defects undetectable by the scoring rules.

### 2.4 Scoring rules

A finding detects a defect when both hold:

1. The finding's type is one the defect accepts. Several types may be accepted, because one real problem can be correctly classified in more than one way — a change-of-control exposure is both a cross-document contradiction and a latent liability, and insisting on a single label would score a correct answer as a miss.
2. At least one anchor phrase appears somewhere in the finding's title, description, or cited spans. Only one is required, because a finding may quote a narrower span than the sentence the defect lives in.

Each finding can claim at most one defect, so a single finding cannot inflate the score.

Leftover findings are split rather than lumped together:

- **Genuine absences that were never planted.** The corpus contains no tax returns, so reporting them missing is correct behaviour and is counted separately.
- **Findings corresponding to nothing real.** These are the noise rate.

---

## 3. Results

```bash
python -m loupe.cli score
```

| | |
| --- | --- |
| **Overall recall** | 7 / 15 (47%) |
| **Noise rate** | 1 / 9 (11%) |
| **Claims extracted** | 232 from 35 documents |

### 3.1 By defect class

| Class | Found | Planted | Recall |
| --- | --- | --- | --- |
| Missing document | 2 | 2 | 100% |
| Undisclosed relationship | 2 | 2 | 100% |
| Temporal impossibility | 1 | 2 | 50% |
| Arithmetic | 1 | 3 | 33% |
| Cross-document contradiction | 1 | 3 | 33% |
| Latent liability | 0 | 3 | 0% |

Both negative-space classes score 100%. That is the clearest positive result: reporting what a corpus does *not* contain is a capability retrieval-based systems structurally lack, and it works reliably here.

Latent liability scores zero on this run, though the same defect was detected on other runs. See section 3.4.

### 3.2 By difficulty

| Difficulty | Found | Planted | Recall |
| --- | --- | --- | --- |
| Easy | 2 | 3 | 67% |
| Medium | 4 | 8 | 50% |
| Hard | 1 | 4 | 25% |

An easy defect being missed while a hard one is found is not an error in the labelling. D-002 is easy in the sense that the two facts sit plainly in two documents — but the critic retracts it as standard commercial practice. D-015 is hard in the sense that it was designed to need coreference — but a literal address match reached it by a route the corpus author did not anticipate.

### 3.3 Every defect

| Defect | Difficulty | Requires | Found |
| --- | --- | --- | --- |
| D-001 Share total does not reconcile | easy | arithmetic reconciliation | yes |
| D-003 Equity incentive plan referenced but absent | easy | negative space audit | yes |
| D-002 Change of control right held by largest customer | easy | cross-document reasoning | no |
| D-006 CFO salary contradicts the board resolution | medium | cross-document comparison | yes |
| D-011 Board consent for CFO appointment absent | medium | reference-driven gap audit | yes |
| D-012 Amendment dated before the amendment it amends | medium | date ordering across documents | yes |
| D-014 Supplier shares an address with the CEO | medium | address matching across documents | yes |
| D-004 Option grants exceed the cap table figure | medium | cross-document arithmetic | no |
| D-005 Revenue schedule exceeds stated total revenue | medium | cross-document arithmetic | no |
| D-007 Deferred revenue stated differently in two documents | medium | cross-document comparison | no |
| D-009 Loan acceleration exceeds available cash | medium | cross-document reasoning | no |
| D-015 Contractor connected to the CTO | hard | coreference and shared address | yes |
| D-008 Revenue recognised on a superseded fee | hard | version handling | no |
| D-010 Direct sale into an exclusive reseller territory | hard | three-document chain, geographic inference | no |
| D-013 Contractor IP created before its assignment | hard | delivery-to-assignment inference | no |

### 3.4 Variance between runs

Three `score` runs over the same corpus and the same response cache, within one session, produced **6, 7, and 8** detections.

The variance traces to a single call. The adversarial critic sometimes retracts the change-of-control finding — arguing that a thirty-day notice period is standard commercial practice — and sometimes confirms it. When it confirms, D-002 and occasionally D-007 are detected; when it retracts, they are not.

Two implications worth stating rather than smoothing over:

**Any single number here carries roughly ±1 defect of uncertainty.** The figures reported are from one run and are reproducible from the committed cache, but a cold run may differ.

**The response cache is not only a cost measure.** Without it, this benchmark would not be reproducible at all, and neither would the ablation study, whose configurations must be compared against a stable baseline.

---

## 4. Ablation study

```bash
python -m loupe.cli ablate
```

Each configuration removes one component and re-scores against the same corpus. Most configurations are subsets of the full pipeline, so their model calls are already cached.

| Configuration | Recall | Noise | Proposed | Confirmed | vs baseline |
| --- | --- | --- | --- | --- | --- |
| Full system | 8/15 (53%) | 0/9 (0%) | 18 | 9 | baseline |
| No pair detector | 5/15 (33%) | 0/6 (0%) | 7 | 6 | −3 defects |
| No tension detector | 8/15 (53%) | 0/9 (0%) | 16 | 9 | no change |
| No entity resolution | 7/15 (47%) | 0/8 (0%) | 17 | 8 | −1 defect |
| No adversarial review | 10/15 (67%) | 7/18 (39%) | 18 | 18 | +2 defects |
| Deterministic only | 4/15 (27%) | 0/5 (0%) | 5 | 5 | −4 defects |

The ablation harness's own baseline run detected 8, one more than the `score` run reported in section 3. Same cause as section 3.4.

### 4.1 The critic trades recall for precision

The most useful number in the study.

Disabling adversarial review raises recall from 8/15 to 10/15 and simultaneously raises the noise rate from 0% to 39%. Eighteen findings are reported instead of nine, and seven of the additional ones correspond to nothing real.

This is the precision–recall tradeoff with a number attached rather than an opinion. It also identifies a specific over-aggression: the critic dismisses D-008 as "a standard contractual progression," which is defensible and wrong.

For a diligence report, precision is the more valuable side. An analyst who encounters seven false findings stops reading, at which point effective recall is zero regardless of what was measured.

### 4.2 The pair detector accounts for most of the recall

Removing targeted pair analysis drops recall from 8 to 5, and both undisclosed-relationship defects are lost.

This validates the separation described in the design document: deciding *which claims to compare* is mechanical and exhaustive; deciding *whether a comparison is a finding* is judgement.

### 4.3 The tension detector contributes nothing

Removing it changes no result. On this corpus it finds only what the pair generator already finds.

This is reported rather than hidden because it is the kind of result a component's author is least inclined to look for. The component remains because it is the more general mechanism — it can surface conflict shapes no rule anticipates — but on this corpus it earns no cost.

### 4.4 Four defects need no model at all

Deterministic detectors alone reach 4/15: arithmetic reconciliation, amendment date ordering, and both gap audits. The full system reaches 8. The model is doing real work, and so is the decision not to use it everywhere.

---

## 5. What debugging the benchmark taught

Three of the eight detections were recovered by fixing bugs rather than adding capability, and the way those bugs were found is worth recording.

**The failure mode was patching without instrumenting.** Cross-document arithmetic produced no findings. Three separate fixes were applied — tightening component selection, restricting document types, adjusting domain matching — and none worked, because each was a guess at the cause.

Printing the intermediate state resolved it in one attempt. The output showed every claim in each domain and which filter had rejected it:

```
drop  120,000    option_grant_schedule    wrong-doctype:other
drop  3,612,000  revenue_by_customer_2025 wrong-doctype:other
```

**The cause was two levels away from the symptom.** The `pairs` command does not run the LLM classifier, so it falls back to a filename heuristic — and that heuristic had no hint matching `option_grant_schedule` or `revenue_by_customer`. Both documents were typed `other`, and the document-type filter silently excluded every component they contained.

Fixing the heuristic recovered the correct sums immediately. Neither the filter nor the classifier was wrong; the fallback path between them was.

The lesson generalises: in a pipeline where each stage transforms the last, a symptom at stage five is rarely caused at stage five. Printing what each stage actually produced is faster than reasoning about what it should produce.

---

## 6. Threats to validity

**The corpus is synthetic and written by the same author as the system.** Both the defects and the detectors reflect one person's model of what goes wrong in a data room. A defect nobody thought to plant cannot be missed, and cannot be measured.

**Thirty-five documents is small.** A real mid-market data room holds several hundred. Gap detection in particular is much easier at this scale, so the low noise rate should not be read as a strong claim.

**Output is not deterministic without the cache.** Section 3.4 quantifies this: ±1 defect between runs.

**Anchor-based scoring is approximate.** A finding matches a defect if one anchor phrase appears anywhere in it. A finding that mentions the right number for the wrong reason would score as a detection. Manual inspection of the seven detections found no such case, but the rule permits it.

**Iterative development against a fixed benchmark risks overfitting.** Several rounds of detection work were performed with this corpus as the target. Each change was assessed against a specific test: *would this help on a data room nobody has seen?* Fixes that only worked because the author knew what a particular defect looked like were deliberately not made — which is why recall stops at 7 rather than being tuned upward.

---

## 7. What the results say to do next

| Work | Recovers | Evidence |
| --- | --- | --- |
| Version handling: an amendment supersedes rather than contradicts | D-008, plus false positives on any real corpus | The no-review ablation recovers D-008, meaning the finding is generated and the critic correctly objects on grounds the system cannot yet address |
| Soften the adjudicator on near-miss reconciliations | D-004, D-005 | Both pairs are now generated with correct arithmetic; the adjudicator rejects them |
| Re-extract the loan agreement | D-009 | The principal was captured as a date sentence, not a numeric claim, so no pair can be formed |
| Multi-hop reasoning over three documents | D-010 | No mechanism exists for chaining beyond a pair |

Two of these — version handling and multi-hop reasoning — are capabilities most systems in this space lack, rather than bug fixes.
