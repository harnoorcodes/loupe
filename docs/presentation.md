# Presentation — 12 slides

Slide text is what goes on screen. Speaker notes are what you say. Keep the on-screen text short; the notes carry the detail.

---

## Slide 1 — Title

**LOUPE**

A jeweller's loupe for the data room

Multi-agent due diligence with verified citations

Your name · Summer School '26 · OpenAI Agents SDK

> **Notes.** A loupe is the magnifier a jeweller uses to inspect a stone for flaws before someone buys it. That is exactly what this system does for a company acquisition.

---

## Slide 2 — The problem

When one company buys another, the buyer gets **two to four weeks** to inspect **several hundred documents**.

Three things go wrong:

- Reviewers are split by speciality, so nobody sees across domains
- Nobody reads everything, so most documents get skimmed
- The missing document leaves no trace, so absence goes unnoticed

> **Notes.** Set up the domain briefly. Don't dwell — the next slide is the one that lands.

---

## Slide 3 — The finding nobody catches

**In the legal folder**

> "Customer may terminate this Agreement upon thirty (30) days written notice"
> — TitanRetail contract, on change of control

**In the financial folder**

> "TitanRetail Group... representing 43% of total revenue"
> — FY2025 statements

Neither is alarming alone.

Together: **acquiring this company destroys 43% of its revenue.**

> **Notes.** This is the whole pitch. Pause after "neither is alarming alone." The legal reviewer sees a standard clause. The accountant sees customer concentration. They work in different rooms and nobody puts the two together. That is the finding this system exists to catch.

---

## Slide 4 — Why the obvious design fails

The obvious approach: one agent per document type.

Legal agent · Financial agent · Compliance agent · Operations agent

**This is an org chart, not an architecture.**

The finding lives *between* two agents' contexts. Neither owns it. Both file clean reports.

> **Notes.** This was the design my assignment brief suggested, and rejecting it is the core decision of the project. Partitioning by document type guarantees you miss the findings that span documents — which are the ones that matter.

---

## Slide 5 — The fix: a shared substrate

```
Documents → Claims → Shared evidence store
                            ↓
             Detectors read across all documents
                            ↓
                  Adversarial review
                            ↓
                    Cited memo
```

Agents are **workers over a shared store**, not owners of a folder.

An agent can reason about documents it never read.

> **Notes.** Every agent writes typed claims to one place. The tension detector then reads all claims about one entity — regardless of which document they came from — and asks what conflicts. That is the architectural inversion.

---

## Slide 6 — Ten agents

**Using a model (5)**
Document Classifier · Claim Extractor · Tension Detector · Red Team Critic · Materiality Scorer

**Deterministic (5)**
Entity Resolver · Arithmetic Detector · Temporal Detector · Gap Auditor · Memo Composer

**Plus:** human approval gate on critical findings

> **Notes.** Half the agents use no model at all. Reconciling a share total is arithmetic. Checking whether a file exists is a fact. Comparing dates is deterministic. Python is faster, free, and right every time. The model is reserved for the five tasks that genuinely need language understanding — and saying so out loud is a design position, not a shortcut.

---

## Slide 7 — Never trust the model with a citation

The model is **never** asked for character positions.

It returns the **exact text it is quoting**. The system finds that text itself.

```
Model says:  "4,250,000"
System does: document.text.find("4,250,000")
Not found?   → claim discarded
```

Every citation is re-validated before it reaches the memo.

> **Notes. ** A model asked for character offsets returns plausible wrong numbers — citations that look right and point at nothing. One hallucinated citation and an analyst never trusts the tool again. So the system is built so it structurally cannot emit an uncited claim.

---

## Slide 8 — Reporting what isn't there

The cap table says:

> "410,000 options granted... under the company equity incentive plan"

**There is no plan document in the data room.**

A mention is not a presence. The reference *is* the defect.

> **Notes.** Retrieval systems can only report what they find. This one holds a checklist of what a complete data room should contain and reports the gaps. And it distinguishes a document being present from a document being mentioned — my first version searched body text, found the phrase, and concluded the plan existed. That bug hid the exact defect it was built to find.

---

## Slide 9 — One agent tries to destroy the others' work

Findings are not trusted on creation.

`proposed → challenged → confirmed | retracted`

The critic is asked to **construct the strongest case that the finding is wrong**.

`Finding.confirm()` raises if the finding was never challenged. Review cannot be skipped.

On the reference run: **2 of 8 findings retracted, 2 severities revised.**

> **Notes.** A reviewer asked "is this correct?" agrees — agreement is the path of least resistance for a language model. A reviewer told to destroy the finding surfaces the rounding artifact and the definitional error. And the lifecycle is enforced by the type system, so there is no code path that admits an unreviewed finding.

---

## Slide 10 — The critic caught my mistake

The arithmetic detector summed founder shares, preferred shares, **and employee options** against the stated total.

All tests passed. Three days of green.

The critic retracted it:

> *"Adding unexercised employee options to issued and outstanding shares is a definitional error."*

**It was right.** Options are not issued shares until exercised.

> **Notes.** This is my favourite result. The corpus, the detector, and the test were all wrong in the same way, so the tests could never catch it. The adversarial agent caught a domain error in my own reasoning. I corrected the corpus — the real defect is 350,000 shares outstanding with no identified holder, which is subtler and more realistic than what I originally planted.

---

## Slide 11 — Results

| Defect | Class | Detected |
| --- | --- | --- |
| D-001 | Arithmetic discrepancy | Yes |
| D-002 | Cross-document liability | Yes |
| D-003 | Missing document | Yes |

**Recall 3/3 · Noise 0/6 · 176 tests · full pipeline cached in <1s**

Measured against a corpus I generated, with defects planted at known locations.

> **Notes.** Most projects in this space cannot tell you whether their output is correct. Because I wrote the corpus, I know exactly what is wrong with it and where — so recall is measured, not asserted. Be honest about the caveat: ten documents is enough to demonstrate the mechanism, not to characterise performance. The cross-document defect is the meaningful result.

---

## Slide 12 — What I would build next

**Now**
- Coreference resolution: "the Company" → Northwind Analytics
- Wider evidence spans covering the full clause, not just the trigger
- A larger corpus with more defect classes

**Later**
- Release the defect-injection corpus as a public benchmark
- Same engine applies to vendor review, insurance underwriting, grant compliance

> **Notes.** The benchmark is the interesting direction. Benchmarks attract more attention than applications, and a public corpus with known planted defects would let anyone measure a diligence system honestly. Close by thanking them and offering to walk through the code.

---

## Delivery notes

- **Twelve slides in ten minutes** is roughly 50 seconds each. Slides 3, 9, and 10 deserve longer; slides 2, 6, and 12 can be quick.
- **Slide 3 is the hook.** If you only land one slide, land that one.
- **Slide 10 is the credibility slide.** Admitting a mistake the system caught is far more convincing than claiming everything worked.
- **Run the demo live if you can** — the cached pipeline finishes in under a second, so there is no risk of waiting on the network in front of an audience.
