# Multi-Agent Design

**Project:** Loupe — a multi-agent due diligence system for M&A data rooms
**Capstone:** Summer School '26, OpenAI Agents SDK

---

## 1. Design principles

### 1.1 Agents are workers over a substrate, not owners of documents

Most multi-agent designs for document review assign one agent per document type: a legal agent, a financial agent, a compliance agent. That partition is the central mistake this system was built to avoid.

The findings that matter in due diligence live *between* documents. A change-of-control clause is unremarkable in isolation. A customer representing 43% of revenue is unremarkable in isolation. Only together do they mean that an acquisition destroys half the target's income. Under a document-type partition, the legal agent sees one half, the financial agent sees the other, and no agent owns the space between them.

Loupe organises agents by **cognitive function over a shared evidence store**. Every agent reads from and writes to a common structure of typed claims. An agent can reason about claims extracted from documents it never read.

### 1.2 Retrieval is mechanical; judgement is not

This is the most consequential decision in the system, and it was reached by measurement rather than design.

The first implementation grouped claims by entity and asked a model to find conflicting pairs within each group. On a 35-document corpus this scored 3 of 15 planted defects. Examining the failures showed why: for most real contradictions, **the two halves belong to different entities**. A stated total is filed under the company; its components are filed under individual people or customers. A supplier's address is filed under the supplier; the founder's address under the founder. Entity grouping structurally cannot bring them together.

The system now separates the two concerns:

- **Which claims are worth comparing** is decided by deterministic Python rules. Exhaustive, free, inspectable.
- **Whether a compared pair is a finding** is decided by a model, one narrow question at a time.

That change took recall from 3/15 to 7/15. The ablation study isolates its contribution at four defects.

### 1.3 Use a model only where judgement is required

Reconciling a share total is arithmetic. Checking whether a file exists is a fact. Comparing two dates is deterministic. These run in Python: faster, free, and correct every time.

Six components use a language model. Six do not. The deterministic detectors alone reach 2 of 15 defects, which is the floor the model has to beat to justify its cost — and it does, reaching 7.

---

## 2. Architecture

```mermaid
flowchart TD
    A[Data room<br/>PDF and DOCX] --> B[Ingestion<br/>text with page and character offsets]
    B --> C[Document Classifier<br/>LLM agent]
    C --> D[Claim Extractor<br/>LLM agent, parallel per document]
    D --> E[Entity Resolver<br/>deterministic]
    E --> F[(Evidence Store<br/>claim graph + append-only finding ledger)]

    F --> G[Arithmetic Detector<br/>deterministic]
    F --> H[Temporal Detector<br/>deterministic]
    F --> I[Gap Auditor<br/>deterministic]
    F --> J[Tension Detector<br/>LLM agent]
    F --> K[Candidate Pair Generator<br/>deterministic]

    K --> L[Pair Adjudicator<br/>LLM agent]

    G --> M[Red Team Critic<br/>LLM agent]
    H --> M
    I --> M
    J --> M
    L --> M

    M --> N[Materiality Scorer<br/>LLM agent]
    N --> O{Human Approval Gate<br/>critical findings only}
    O --> F
    F --> P[Memo Composer<br/>deterministic]
    P --> Q[Findings memo<br/>with resolvable citations]
```

The evidence store sits at the centre deliberately. Agents do not message each other in prose; they read and write typed objects in a shared structure. That is what makes cross-document reasoning possible rather than merely aspirational.

---

## 3. Agent roles

### 3.1 Agents using a language model

| Agent | Model role | Mission |
| --- | --- | --- |
| Document Classifier | extraction | Identify what kind of document each file is, by reading it |
| Claim Extractor | extraction | Turn document text into typed, cited claims |
| Tension Detector | reasoning | Compare claims about one entity across documents |
| Pair Adjudicator | reasoning | Judge candidate pairs selected by deterministic rules |
| Red Team Critic | critic | Attempt to destroy every proposed finding |
| Materiality Scorer | reasoning | Estimate monetary impact relative to deal size |

### 3.2 Deterministic agents

| Agent | Mission |
| --- | --- |
| Entity Resolver | Merge name variants so claims about one company group together |
| Candidate Pair Generator | Decide which claims are worth comparing |
| Arithmetic Detector | Reconcile stated totals against their components |
| Temporal Detector | Find events dated impossibly relative to each other |
| Gap Auditor | Report expected documents that are absent |
| Memo Composer | Render confirmed findings into a report |

### 3.3 Human in the loop

| Component | Mission |
| --- | --- |
| Approval Gate | Require explicit human sign-off on critical findings before reporting |

---

## 4. Agent detail

### Document Classifier

**Input:** the opening 400 characters of each readable document, batched twelve at a time.
**Output:** a document type per file, with a stated reason.
**Model:** cheap extraction model.

Before this agent, document type was inferred from the filename. That works on a tidy corpus and fails on a real one, where files carry client reference numbers or names like `Doc1_final_v3_SIGNED.pdf`. Reading the opening text is more robust, because a document announces what it is in its first paragraph.

Batching matters: an earlier version processed only the first twenty documents and silently fell back to the filename heuristic for the rest, misclassifying the option grant schedule and the revenue breakdown as `other`. Batches now cover the whole corpus and run concurrently.

*Observed behaviour:* reclassified 13 of 35 documents on the reference corpus, including `ip_assignment.docx` from `other` to `contract` and `option_grant_schedule.docx` from `other` to `cap_table`.

### Claim Extractor

**Input:** document blocks, batched six at a time.
**Output:** typed claims, each bound to an exact source span.
**Model:** cheap extraction model, parallel across documents.

The critical design decision concerns provenance.

> **The model is never asked for character offsets. It returns the exact text it is quoting, and the system locates that text itself.**

A model asked for offsets will confidently return plausible wrong numbers, producing citations that look correct and point at nothing. By requiring a verbatim quote and locating it with a string search, a fabricated quote resolves to nothing and the claim is discarded rather than emitted with a broken citation.

Claims are atomic. "The company has 4,250,000 shares and 12 employees" is two claims, not one. Atomicity is what makes cross-document comparison mechanical rather than interpretive.

*Observed behaviour:* 232 claims from 35 documents.

### Entity Resolver

**Input:** raw subject strings from extracted claims.
**Output:** a canonical key per entity.

Extraction produces variants of the same name: "TitanRetail Group Limited" and "TitanRetail Group", "Northwind Analytics Inc." and "Northwind Analytics". Grouping and pairing both depend on subject identity, so unmerged variants mean the claims are never compared.

This is deliberately not a full entity resolver. It is suffix stripping and case folding: no model call, no cost, deterministic. Coreference — "the Company", "the Executive" — is unresolved and appears in the claim graph as its own entity.

*Measured contribution:* the ablation shows removing it costs one defect.

### Candidate Pair Generator

**Input:** the whole claim graph.
**Output:** pairs of claims that a rule considers worth comparing.
**No model.**

Four rules, each targeting a class of contradiction that entity grouping cannot reach:

| Rule | Selects | Guards against |
| --- | --- | --- |
| **Numeric mismatch** | Two claims stating the same measure with different values | Generic measures across unrelated subjects; different reporting periods; authorised capital compared to issued |
| **Total versus components** | A stated total and the parts that should sum to it | Components from the same document as the total; proportions treated as amounts; stray small numbers |
| **Shared address** | One street address appearing in two documents for different parties | Same-entity pairs |
| **Trigger and magnitude** | A right or condition beside an amount concerning the same party | Routine notice periods filed under the company, which would otherwise pair with every figure in the corpus |

The guards are not incidental. A first implementation produced 49 candidate pairs on the reference corpus, most of them noise: two founders' shareholdings compared against each other, FY2024 revenue against FY2025, a 60-day notice period paired with all nine financial figures. Five specific fixes reduced this to 26 pairs with no loss of defect coverage.

Because generation is deterministic and free, the candidates can be inspected before any model call:

```bash
python -m loupe.cli pairs
```

### Pair Adjudicator

**Input:** candidate pairs, batched six per call, each with the reason it was selected.
**Output:** a verdict per pair.
**Model:** reasoning model.

The division of labour is the point. Retrieval was mechanical; this is the judgement. Because each pair arrives with its selection reason, the model answers a narrow question about two specific claims rather than searching a list of thirty for something interesting.

The prompt is explicit that most pairs will be innocent and that saying so is correct. It is also explicit that a false finding costs more than a missed one, because an analyst who stops trusting the report stops reading it.

*Observed behaviour:* 11 findings proposed from 26 candidate pairs.

### Tension Detector

**Input:** all claims about one entity, drawn from multiple documents.
**Output:** cross-document conflict findings.
**Model:** reasoning model.

The prompt design decision:

> **The agent is asked "what conflicts here?" — never "find risks."**

A model asked to find risks will find them, because that is what it was asked to do. It will produce fluent, plausible, unfalsifiable risks. Asked instead what conflicts between specific claims it can see, it must either point at two of them or return nothing.

Every reported conflict must cite two claim IDs from the list supplied. A conflict citing an ID that was never given is discarded — the equivalent of span validation.

*Measured contribution: none.* The ablation shows removing this agent changes no result. It finds only what the pair generator already finds. It is retained because it is the more general mechanism and would catch conflict shapes no rule anticipates, but the honest reading is that on this corpus it earns no cost.

### Arithmetic Detector

**Input:** quantity claims about shares and equity.
**Output:** reconciliation findings.
**No model.**

Three hazards handled explicitly:

1. **Duplicate claims.** The same founder holding appears in the cap table and in their employment agreement. Naive summing double-counts. Claims are deduplicated by value, preferring the cap table as authoritative.
2. **Total versus component ambiguity.** An option pool described as "outstanding" carries a total marker but is a component. Only the largest stated total is reconciled against.
3. **Defined terms.** "Issued and outstanding" excludes unexercised options; "fully diluted" includes them. Conflating the two is a definitional error, not a discrepancy. See section 7.

### Temporal Detector

**Input:** claims and documents containing parseable dates.
**Output:** ordering-impossibility findings.
**No model.**

Two checks: events dated before the company's incorporation, and an amendment dated before the amendment it claims to modify.

*Observed behaviour:* neither check fires on the reference corpus. The amendment check requires both documents to expose a parseable date and an amendment number in their opening text, and does not match the corpus phrasing. This is a known gap rather than a passing test.

### Gap Auditor

**Input:** the corpus and a diligence request list of 14 expected documents.
**Output:** missing-document findings.
**No model.**

This agent reports what is *absent*, which retrieval systems structurally cannot do. It rests on one distinction:

> **A document being present is not the same as a document being mentioned.**

The cap table states that options were granted "under the company equity incentive plan". No such plan exists in the corpus. Searching document body text for keywords would treat that mention as proof of presence and hide the exact defect the audit is for. Presence is matched against filenames only; body text is used for a different purpose — deciding whether an item applies at all.

That conditional logic is what makes the finding meaningful. An equity incentive plan is reported missing *because the corpus shows options were granted*, not because a generic checklist listed one.

### Red Team Critic

**Input:** every proposed finding, with evidence, reviewed in a single call.
**Output:** confirm or retract, with the objection recorded.
**Model:** critic model.

The critic is not asked to review a finding. It is asked to **destroy** it.

A reviewer asked "is this correct?" agrees, because agreement is the path of least resistance for a language model. A reviewer instructed to construct the strongest case against a finding surfaces the rounding artifact, the superseded amendment, the definitional error — and when it cannot, the finding has earned its place.

Reviewing all findings in one call also gives the critic sight of the other findings, so it can detect that two findings describe the same issue. On the reference corpus it retracted four findings as duplicates of one another.

Before any model call, every citation is re-validated against its source document. A finding whose evidence does not resolve is retracted automatically and never consumes a model call.

*Measured contribution:* the ablation shows the critic costs one defect and removes seven false positives. Disabling it raises recall from 7/15 to 8/15 and raises the noise rate from 0% to 44%.

### Materiality Scorer

**Input:** confirmed findings and the transaction value.
**Output:** an estimated monetary impact and a revised severity.
**Model:** reasoning model.

Severity labels are weak decision inputs. "High" tells a buyer to worry; a dollar figure tells them how much, and whether it justifies renegotiating the price.

The agent may use only figures that appear in the finding's own evidence, and is instructed to report `quantifiable: false` when it cannot ground an estimate. An invented figure in a diligence memo is worse than no figure.

*Observed behaviour:* quantifies the share discrepancy and the salary gap; correctly declines to quantify missing-document findings.

### Approval Gate

**Input:** confirmed findings.
**Output:** findings with a human decision recorded.

Critical-severity findings require explicit sign-off before entering the memo.

The gate is deliberately placed *after* adversarial review. A human asked to approve twenty unreviewed findings will rubber-stamp them. A human asked to approve two that already survived a hostile critic is making a real decision. The critic's objection is displayed alongside the finding, so the reviewer sees what was argued against it rather than only the conclusion.

### Memo Composer

**Input:** the confirmed finding ledger.
**Output:** a markdown memo with citations.
**No model.**

The memo is a *rendering* of the ledger, never a separate act of writing. It cannot introduce a claim not already in the ledger. Because no model is called, the memo cannot hallucinate, cannot vary between runs, and costs nothing.

---

## 5. Interaction and handoff flow

```mermaid
sequenceDiagram
    participant U as Analyst
    participant CL as Classifier
    participant EX as Extractor
    participant ST as Evidence store
    participant CG as Pair generator
    participant PA as Pair adjudicator
    participant RC as Red team critic
    participant MS as Materiality scorer
    participant MC as Memo composer

    U->>CL: upload corpus
    CL->>ST: document types
    EX->>ST: typed claims with spans
    Note over ST: claims from all documents<br/>now in one place

    CG->>ST: read claims
    Note over CG: deterministic rules select<br/>which claims to compare
    CG->>PA: candidate pairs with reasons
    PA->>RC: proposed findings

    Note over RC: revalidates every citation<br/>before spending a model call
    RC->>RC: construct strongest objection
    RC->>MS: findings that survived
    RC-->>ST: retracted findings, with reasons

    MS->>U: critical findings for approval
    U->>ST: approve or reject
    ST->>MC: confirmed ledger
    MC->>U: memo with resolvable citations
```

### Handoff conditions

| From | To | Condition |
| --- | --- | --- |
| Classifier | Extractor | Document is readable |
| Extractor | Evidence store | Quote resolves to real source text |
| Pair generator | Pair adjudicator | A rule selected the pair |
| Any detector | Red team critic | A finding is proposed |
| Red team critic | Materiality scorer | Finding survived the objection |
| Red team critic | Ledger (retracted) | Objection succeeded, or citation failed validation |
| Materiality scorer | Approval gate | Severity is critical |
| Ledger | Memo composer | Status is confirmed |

The lifecycle is enforced by the type system rather than by convention. `Finding.confirm()` raises an exception unless the finding was challenged first, so no code path can admit an unreviewed finding to the memo.

```mermaid
stateDiagram-v2
    [*] --> Proposed: detector raises
    Proposed --> Challenged: critic objects
    Challenged --> Confirmed: objection insufficient
    Challenged --> Retracted: objection succeeds
    Confirmed --> Retracted: human rejects
    Confirmed --> [*]: enters memo
    Retracted --> [*]: appendix only
```

---

## 6. Tool and integration overview

| Integration | Used by | Purpose |
| --- | --- | --- |
| PDF text extraction (`pypdf`) | Ingestion | Text with page boundaries preserved |
| DOCX text extraction (`python-docx`) | Ingestion | Paragraph and table text |
| Gemini API via OpenAI-compatible endpoint | All LLM agents | Model inference |
| Span validator | Extractor, Critic | Verify a citation against source text |
| Claim retrieval by entity | Tension detector | Cross-document claim lookup |
| Entity normaliser | Evidence store, pair generator | Merge name variants |
| Candidate pair rules | Pair generator | Select claims worth comparing |
| Diligence request list | Gap auditor | Expected-document checklist |
| Evidence store persistence | All agents | JSON claim graph and append-only ledger |
| Response cache | All LLM agents | Content-hashed disk cache |
| Ablation harness | Evaluation | Component contribution measurement |

### Notes on the model integration

The OpenAI Agents SDK supplies the orchestration framework; the model behind it is swappable. Four provider-specific issues are handled in `src/loupe/llm/provider.py`:

1. **No Responses API.** Gemini does not implement it, so `OpenAIChatCompletionsModel` is pinned rather than relying on the SDK default.
2. **Tracing.** The SDK's default trace exporter uploads to OpenAI and fails without an OpenAI key. It is disabled.
3. **Structured output.** Schema enforcement is less strict than OpenAI's, so a validate-repair-retry layer is mandatory rather than optional.
4. **Rate limits.** Concurrency is capped and requests retry with exponential backoff and jitter.

Agents request a **model role** — `extraction`, `reasoning`, or `critic` — and the mapping to a concrete model identifier lives in configuration. During development, `gemini-2.5-flash` was found still listed in the provider's model catalogue while being closed to new users. Making model identifiers configuration rather than code meant that discovery cost one line rather than a refactor.

---

## 7. Memory and context management

| Layer | Contents | Lifetime |
| --- | --- | --- |
| Document store | Parsed text and blocks with span coordinates | Per run |
| Claim graph | Typed claims indexed by document and by entity | Persisted |
| Finding ledger | Append-only, versioned findings | Persisted |
| Progress record | Which documents have been extracted | Persisted |
| Response cache | Model responses keyed by content hash | Persisted |

Three properties matter.

**The ledger is append-only.** A lifecycle transition writes a new entry rather than editing the old one, so the audit trail records what was proposed, what was objected to, and what was decided. `current_findings()` returns the latest version of each finding, so history is retained without polluting output.

**Extraction is checkpointed.** Documents already processed are skipped on a re-run, so an interrupted run resumes rather than repeating work. This was exercised in practice when a free-tier rate limit interrupted a run mid-corpus.

**Model responses are cached by content hash.** Prompt and model identity form the key. A repeated run produces identical output at no cost, which makes both the demonstration and the ablation study reproducible.

---

## 8. What adversarial review actually caught

The clearest evidence that the critic mechanism works is that it caught an error in the system's own design.

The arithmetic detector originally reconciled a cap table by summing founder holdings, preferred shares, **and employee options** against the stated total. All tests passed. The planted defect was described in terms of that sum.

The critic retracted the finding with this objection:

> *Adding unexercised employee options to issued and outstanding shares is a definitional error.*

It is correct. "Issued and outstanding" is a term of art that excludes unexercised options; options are not issued shares until exercised. The detector, the corpus, and the test were all wrong in the same way, and three days of passing tests had not surfaced it.

The corpus and detector were corrected. The real discrepancy is 350,000 shares stated as outstanding with no identified holder — a subtler and more realistic defect than the one originally planted.

---

## 9. Known weaknesses

Stated as design facts rather than as future work.

**The critic is over-aggressive.** It retracts D-008, a genuine finding about revenue recognised on a superseded contract fee, as "a standard contractual progression." The ablation quantifies the cost at one defect.

**The tension detector is redundant.** Removing it changes no result.

**Coreference is unresolved.** "The Company" appears in the claim graph as an entity distinct from Northwind Analytics, fragmenting six claims away from the entity they belong to.

**No version handling.** An amendment that supersedes a term is treated as contradicting it. This is the direct cause of D-008's retraction and would produce false positives on any real data room, which are full of amendments.

**The temporal detector does not fire.** Its amendment-ordering check does not match the corpus phrasing.

**Evidence spans can be narrower than the clause they describe.** The change-of-control finding cites the notice period rather than the trigger.
