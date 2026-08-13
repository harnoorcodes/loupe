# Loupe

**A jeweller's loupe for the data room.**

A multi-agent system that reads an M&A data room, finds contradictions *between* documents, reports what the data room is missing, and cites every claim to an exact page and character span.

Built on the OpenAI Agents SDK, running on Google Gemini.

---

## Results

Measured against a synthetic corpus with defects planted at known locations, so detection is verified rather than asserted.

| Defect | Class | Detected |
| --- | --- | --- |
| D-001 | Arithmetic: share total does not reconcile | Yes |
| D-002 | Cross-document latent liability | Yes |
| D-003 | Missing document | Yes |

**Recall: 3/3. Findings corresponding to nothing real: 0 of 6.**

Three further findings report documents genuinely absent from the corpus but never planted. Reporting them is correct behaviour, so they are counted separately rather than as errors.

A ten-document corpus makes gap detection easy, so the low noise rate is not a strong claim on its own. Recall on the cross-document defect is the meaningful result.

```bash
python -m loupe.cli score
```

---

## The problem

In an acquisition, the buyer gets a few weeks to inspect several hundred documents. The risks that matter are almost never inside one document — they emerge from the gap between two:

> **In the legal folder:** a customer contract lets the counterparty walk away if the supplier is acquired.
>
> **In the financial folder:** that same customer is 43% of revenue.

Neither document is alarming alone. The legal reviewer sees a routine clause. The financial reviewer sees customer concentration. Because reviewers are partitioned by domain, nobody holds both facts at once — and the buyer discovers the problem after closing.

Two further gaps in current practice:

- **Sampling.** Nobody reads all several hundred documents carefully. Large contracts get read; the rest get skimmed. Problems survive in the skimmed material.
- **Absence.** The most dangerous item is often the document that isn't there. An absent document leaves no artifact, so nothing represents it.

---

## The approach

Most designs for this problem assign one agent per document type: a legal agent, a financial agent, a compliance agent. That partition is the bug. It puts the cross-document contradiction in the space *between* agents, where nothing owns it.

Loupe inverts this. Agents are workers over a **shared evidence store**, not owners of a document category. An agent can reason about claims extracted from documents it never read.

```
Data room + request list
           |
   Document Classifier -- Claim Extractor -- Entity Resolver
           |
   Claim graph + evidence store          <- the shared substrate
           |
   +-------+-------+----------+
Arithmetic Temporal Gap      Tension
 detector  detector auditor   detector
   +-------+-------+----------+
           |
    Red Team Critic                      <- tries to destroy every finding
           |
   Materiality Scorer
           |
    Human approval (critical only)
           |
     Finding ledger -> memo              <- memo is only a rendering
```

Four mechanisms carry most of the weight.

**Provenance or abstain.** Every claim resolves to a `(document, page, character range)` tuple. The model is never asked for character offsets — it returns the exact text it is quoting, and the system locates that text itself. A fabricated quote resolves to nothing and the claim is discarded. A validator re-checks every citation before it reaches the memo.

**Adversarial review.** Findings move `proposed → challenged → confirmed | retracted`. The critic is not asked to review a finding; it is asked to construct the strongest case that the finding is wrong. Only survivors reach the memo. `Finding.confirm()` raises on an unchallenged finding, so review cannot be skipped by accident.

**Negative space.** The system holds a diligence request list describing what a complete data room should contain, and reports every unfulfilled item. Crucially, a document being *mentioned* is not treated as a document being *present* — the cap table refers to an equity incentive plan that does not exist, and that reference is the defect, not evidence against it.

**A model only where judgement is required.** Reconciling a share total is arithmetic. Checking whether a file exists is a fact. Comparing dates is deterministic. These run in Python: faster, free, correct every time. Five agents use a model; five do not.

---

## What adversarial review caught

The clearest evidence the critic works is that it caught an error in the system's own design.

The arithmetic detector originally summed founder holdings, preferred shares, **and employee options** against the stated cap table total. All tests passed. The planted defect was described in those terms.

The critic retracted the finding:

> *Adding unexercised employee options to issued and outstanding shares is a definitional error.*

It was right. "Issued and outstanding" excludes unexercised options; options are not issued shares until exercised. The detector, the corpus, and the test were all wrong in the same way, and three days of green tests had not surfaced it.

The corpus and detector were corrected. The real discrepancy is 350,000 shares stated as outstanding with no identified holder — a subtler and more realistic defect than the one originally planted.

---

## Agents

**Using a language model**

| Agent | Role |
| --- | --- |
| Document Classifier | Identifies document type by reading the text, not the filename |
| Claim Extractor | Turns text into typed, cited claims. Runs in parallel per document |
| Tension Detector | Finds contradictions between claims from different documents |
| Red Team Critic | Attempts to destroy every proposed finding |
| Materiality Scorer | Estimates monetary impact relative to deal size |

**Deterministic**

| Agent | Role |
| --- | --- |
| Entity Resolver | Merges name variants so claims about one company group together |
| Arithmetic Detector | Reconciles stated totals against components |
| Temporal Detector | Finds impossible date orderings |
| Gap Auditor | Reports expected documents that are absent |
| Memo Composer | Renders confirmed findings into a report |

Plus a **human approval gate** on critical findings, placed after adversarial review rather than before — a human asked to approve twenty unreviewed findings will rubber-stamp them; a human asked to approve two that survived a hostile critic is making a real decision.

Full detail in [`docs/02-multi-agent-design.md`](docs/02-multi-agent-design.md).

---

## Getting started

### Requirements

- Python 3.11 or newer
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey) — the free tier is sufficient

### Setup

```bash
git clone https://github.com/harnoorcodes/loupe.git
cd loupe

python -m venv .venv
source .venv/Scripts/activate    # Windows (Git Bash)
# source .venv/bin/activate      # macOS / Linux

pip install -r requirements.txt
pip install -e .

cp .env.example .env
# edit .env and add your key
```

### Verify

```bash
python -m loupe.cli check
```

Prints resolved configuration, the model routing table, the safety check, and confirms a live model call.

### Run the full pipeline

```bash
python scripts/generate_corpus.py    # create the synthetic data room
python -m loupe.cli extract          # extract claims from every document
python -m loupe.cli detect --fresh   # find, review, and score findings
python -m loupe.cli score            # measure against planted defects
python -m loupe.cli memo             # write the findings memo
```

The memo lands at `data/memo.md`.

### Tests

```bash
pytest
```

176 tests, all offline. No network calls, no API cost.

---

## Configuration

All configuration lives in `.env`. Nothing in the codebase reads environment variables directly — everything goes through a validated settings object, so a bad value fails at startup rather than silently at call time.

| Variable | Default | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | — | Required |
| `GEMINI_MODEL` | `gemini-3.5-flash` | Default model identifier |
| `GEMINI_TIER` | `free` | `free` or `paid`; gates real-document processing |
| `ALLOW_REAL_DOCUMENTS` | `false` | Must be `true` and tier `paid` to process real data |
| `MAX_DOCUMENTS_PER_RUN` | `250` | Denial-of-wallet ceiling |
| `LOG_LEVEL` | `INFO` | |

### Why models are configuration, not code

During development, `gemini-2.5-flash` was found still listed in the provider's model catalogue while being closed to new users. Availability is not the same as visibility.

Agents therefore request a **role** — `extraction`, `reasoning`, or `critic` — and the mapping to a concrete model identifier lives in configuration. Model retirement is a one-line change. It also allows routing a cheap model to high-volume extraction and a capable one to cross-document reasoning.

---

## Running the Agents SDK without an OpenAI key

The SDK provides the orchestration framework; the model behind it is swappable. Four things need handling when the provider is Gemini, all in `src/loupe/llm/provider.py`:

1. **No Responses API.** Gemini does not implement it. Pin `OpenAIChatCompletionsModel` rather than relying on the SDK default, or every call returns 404.
2. **Tracing.** The default trace exporter uploads to OpenAI and returns 401 without an OpenAI key. Disable it or configure an alternative processor.
3. **Structured output.** Schema enforcement is less strict than OpenAI's, so a validate-repair-retry layer is required rather than optional.
4. **Rate limits.** Concurrency is capped and requests retry with exponential backoff and jitter.

A content-hashed disk cache sits in front of every model call, so a repeated run costs nothing and produces identical output. The full pipeline runs in under a second when cached.

---

## Security

| Threat | Mitigation |
| --- | --- |
| **Prompt injection via uploaded documents** | Document text is delimited and marked untrusted; extraction agents hold no tools and no handoff ability, so the most exposed agents have the least authority |
| **Data exposure to the provider** | A runtime guard refuses real documents on a free-tier key; enforced in code and covered by test |
| **Sensitive text in logs** | The logging layer redacts content-bearing fields; logs carry document IDs and span coordinates only |
| **Denial of wallet** | Document count and token ceilings |
| **Ledger tampering** | Append-only ledger; corrections are versioned entries, not in-place edits |

Prompt injection is a live threat here rather than a theoretical one. The party who assembled the data room has a direct financial interest in incomplete review, and controls the input the system reads.

---

## Limitations

- **Evidence spans can be narrower than the clause they describe.** The change-of-control finding cites the notice period rather than the full clause.
- **Entity resolution handles suffix variants only.** Coreference such as "the Company" is unresolved.
- **The corpus is small.** Ten documents demonstrates the mechanism; it does not characterise performance.
- **Materiality is conservative.** The scorer declines to quantify more often than needed. Correct failure direction, but it leaves value on the table.
- **No OCR.** Scanned documents are flagged as unreadable and listed in the gap report rather than silently mis-parsed.

---

## Scope

**In scope:** single-deal analysis, B2B SaaS acquisitions in the USD 5–50M range, PDF and DOCX, four workstreams (financial, legal, corporate, compliance).

**Out of scope:** OCR, live integrations, multi-deal portfolios, non-English corpora, deals above USD 50M where the diligence process differs structurally.

Loupe does not decide whether to proceed with a transaction, provide legal advice, or produce a valuation. It surfaces findings with evidence; a qualified human decides.

---

## Documentation

- [`docs/01-problem-analysis.md`](docs/01-problem-analysis.md) — business context, stakeholders, requirements, personas, threat model
- [`docs/02-multi-agent-design.md`](docs/02-multi-agent-design.md) — agent architecture, roles, handoff flow, tool integration

---

## Licence

MIT
