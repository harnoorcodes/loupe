# Loupe

**A jeweller's loupe for the data room.**

A multi-agent system that reads an M&A data room, finds contradictions *between* documents, reports what the data room is missing, and cites every claim to an exact page and character span.

Built on the OpenAI Agents SDK, running on Google Gemini.

> **Status: in development.** Milestones 0 and 1 complete. See [Build status](#build-status) for what currently works. Evaluation results are not yet available — this README will not claim numbers it cannot produce.

---

## The problem

In an acquisition, the buyer gets a few weeks to inspect several hundred documents. The risks that matter are almost never inside one document — they emerge from the gap between two:

> **In the legal folder:** a customer contract lets the counterparty walk away if the supplier is acquired.
>
> **In the financial folder:** that same customer is 43% of revenue.

Neither document is alarming alone. The legal reviewer sees a routine clause. The financial reviewer sees customer concentration. Because reviewers are partitioned by domain, nobody ever holds both facts at once — and the buyer discovers the problem after closing.

Two further gaps in current practice:

- **Sampling.** Nobody reads all several hundred documents carefully. The big contracts get read; the rest get skimmed. Problems survive in the skimmed material.
- **Absence.** The most dangerous item is often the document that isn't there — an unsigned consent, a missing amendment. An absent document leaves no artifact, so nothing represents it.

---

## The approach

Most designs for this problem assign one agent per document type: a legal agent, a financial agent, a compliance agent. That partition is the bug. It puts the cross-document contradiction in the space *between* agents, where nothing owns it.

Loupe inverts this. Agents are workers over a **shared substrate**, not owners of a document category.

```
Data room + request list
           |
    Claim extractors  ---  Entity resolver
           |
   Claim graph + evidence store        <-- the shared substrate
           |
  Tension detector  ---  Gap auditor
           |
    Domain verifiers                   <-- adjudicate on demand
           |
     Red team critic                   <-- tries to falsify every finding
           |
      Finding ledger                   <-- memo is only a rendering
```

Three mechanisms carry most of the weight:

**Provenance or abstain.** Every claim resolves to a `(document, page, character range)` tuple. A post-generation validator re-checks each citation against source text; unverifiable spans cause the finding to be retracted, not softened. The system is architecturally incapable of an uncited assertion.

**Adversarial review.** Findings move `proposed → challenged → confirmed | retracted`. The critic agent is not asked to review a finding — it is asked to construct the strongest case that the finding is wrong. Only survivors reach the ledger.

**Negative space.** The system is initialised with a diligence request list describing what a complete data room should contain, and reports every unfulfilled item as a first-class finding. Retrieval systems can only report what they find; this one reports what is absent.

---

## Evaluation

Most projects in this space cannot tell you whether their output is correct. This one is measured against ground truth.

A synthetic data room is generated for a fictional company, with defects of known type and location deliberately planted:

| Defect class | Example |
| --- | --- |
| `ARITHMETIC` | Cap table share count does not equal the sum of grants plus options |
| `CROSS_DOC_CONTRADICTION` | A contract term contradicts revenue recognition in the financials |
| `TEMPORAL_IMPOSSIBILITY` | An amendment dated before the agreement it amends |
| `LATENT_LIABILITY` | A change-of-control clause voiding a material contract on acquisition |
| `MISSING_DOCUMENT` | Option grants exist with no equity incentive plan |
| `UNDISCLOSED_RELATIONSHIP` | A vendor sharing an address with a founder |

Because the corpus is generated, ground truth is exact. This yields recall, precision, and false-positive rate **per defect class**.

> Results table will appear here once the harness is built. No numbers are claimed before then.

Targets: recall ≥ 0.80 overall, ≥ 0.70 on cross-document defects, ≤ 3 false positives per 100 documents, and 100% of emitted citations resolving to real source text.

The false-positive target matters as much as recall. A report with 200 findings of which 190 are noise gets abandoned around finding 30, at which point effective recall is zero regardless of the measured number.

---

## Build status

| Milestone | Scope | Status |
| --- | --- | --- |
| 0 | Verify Agents SDK runs on Gemini — completions, tool calling, structured output | Complete |
| 1 | Package skeleton, typed settings, provider factory, structured logging, tests | Complete |
| 2 | Document model — `Span`, `Block`, `Claim`, `Finding`; span validator | Not started |
| 3 | Ingestion — PDF/DOCX parsing with page and offset preservation | Not started |
| 4 | Claim extraction agents | Not started |
| 5 | Entity resolution | Not started |
| 6 | Tension detection | Not started |
| 7 | Gap auditing | Not started |
| 8 | Domain verifiers and red team critic | Not started |
| 9 | Synthetic data room and defect injection harness | Not started |
| 10 | Memo generation and CLI | Not started |

---

## Getting started

### Requirements

- Python 3.11 or newer
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey) — free tier is sufficient for development

### Setup

```bash
git clone <repository-url>
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

Prints resolved configuration, the model routing table, the safety check result, and confirms a live model call.

```bash
pytest
```

Runs the offline test suite. No network calls, no API cost.

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

During initial setup, `gemini-2.5-flash` was found to still appear in the provider's model listing while being closed to new users. Availability is not the same as visibility.

Agents therefore request a **role** — `extraction`, `reasoning`, or `critic` — and the mapping to a concrete model identifier lives in configuration. Model retirement is a one-line change. It also allows routing cheap models to high-volume mechanical extraction and capable models to cross-document reasoning.

---

## Notes on running the Agents SDK without an OpenAI key

The Agents SDK provides the orchestration framework; the model behind it is swappable. Four things need handling when the provider is Gemini:

1. **No Responses API.** Gemini does not implement it. Pin `OpenAIChatCompletionsModel` rather than relying on the default. Responses-only tool features are unavailable.
2. **Tracing 401s.** Traces upload to OpenAI and fail without an OpenAI key. Disable the default exporter or configure an alternative processor.
3. **Structured output.** Schema enforcement is less strict than OpenAI's. A validate-repair-retry layer is required rather than optional.
4. **Streamed tool calls.** Some compatible providers emit tool-call deltas unreliably; buffering may be needed.

All four are handled in `src/loupe/llm/provider.py`.

---

## Security

| Threat | Mitigation |
| --- | --- |
| **Prompt injection via uploaded documents** | Document text delimited and marked untrusted; extraction agents hold no tools or handoffs; injection attempts are reported as findings |
| **Data exposure to provider** | Runtime guard refuses real documents on a free-tier key; enforced in code and covered by test |
| **Sensitive text in logs** | Logging layer redacts content-bearing fields; logs carry document IDs and span coordinates only |
| **Denial of wallet** | Document count, page, and token ceilings; cost estimate before execution |
| **Ledger tampering** | Append-only ledger; corrections are versioned entries, not in-place edits |

Prompt injection is a live threat here rather than a theoretical one. The party who assembled the data room has a direct financial interest in incomplete review, and controls the input the system reads.

---

## Scope

**In scope for V1:** single-deal analysis, B2B SaaS acquisitions in the USD 5–50M range, PDF and DOCX, four workstreams (financial, legal, corporate, compliance).

**Out of scope for V1:** OCR of scanned documents, live integrations, multi-deal portfolios, non-English corpora, real-time collaboration, deals above USD 50M where the diligence process differs structurally.

Loupe does not decide whether to proceed with a transaction, provide legal advice, or produce a valuation. It surfaces findings with evidence; a qualified human decides.

---

## Documentation

- [`docs/01-problem-analysis.md`](docs/01-problem-analysis.md) — business context, stakeholders, requirements, personas, edge cases, threat model

---

## Licence

MIT
