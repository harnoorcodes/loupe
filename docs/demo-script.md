# Demo video script

**Target length:** 7 minutes (assignment allows 5–10)
**Format:** screen recording with voiceover
**Tool:** OBS Studio, Loom, or Windows Game Bar (`Win + G`)

---

## Before you record

Run this once so every model call is cached. The recorded run then completes in under a second with no network dependency:

```bash
python -m loupe.cli detect --fresh --no-approval
```

Then reset for the take:

```bash
rm -f data/run/findings.json
clear
```

**Checklist**

- [ ] Terminal font enlarged (Ctrl + Shift + `+` in most terminals) — small text is unreadable in a compressed video
- [ ] Terminal maximised, notifications silenced
- [ ] These files open in tabs, ready to switch to: `data/synthetic/contract_titanretail.pdf`, `data/synthetic/financial_statements_2025.pdf`, `data/memo.md`
- [ ] Microphone tested
- [ ] This script on a second screen or printed

**Recording tip:** record in one take if you can. Small stumbles are fine and read as authentic. A heavily edited video reads as rehearsed.

---

## 0:00–0:50 — The problem

**Show:** the two PDFs side by side, scrolled to the relevant sections.

> "When one company buys another, the buyer gets a few weeks to read several hundred documents. I want to show you the kind of thing that gets missed.
>
> This is a customer contract. Section 11 — change of control. If the supplier is acquired, this customer can walk away on thirty days notice, no penalty.
>
> [switch to financials]
>
> And this is the financial statement. That same customer, TitanRetail, is 43% of total revenue.
>
> Neither document is alarming on its own. The lawyer sees a standard clause. The accountant sees customer concentration. They work separately, so nobody puts the two together — and the buyer finds out after closing that they've just destroyed half the revenue they paid for.
>
> That's what this system is built to catch."

---

## 0:50–1:40 — What it is

**Show:** the repo in your editor, `src/loupe/agents/` folder expanded.

> "This is Loupe. It's a multi-agent system built on the OpenAI Agents SDK, running on Gemini.
>
> Ten agents. Five use a language model — a document classifier, a claim extractor, a tension detector, a red team critic, and a materiality scorer. Five are deterministic Python — entity resolution, arithmetic, dates, gap auditing, and report generation.
>
> That split is deliberate. Reconciling a share total is arithmetic, not judgement. Checking whether a file exists is a fact. Those don't need a model, and Python is faster, free, and right every time.
>
> The important design decision is that agents don't own document types. Most designs for this problem give you a legal agent and a financial agent — but then the contradiction I just showed you falls between them and nobody owns it. Here, every agent reads and writes to one shared evidence store, so an agent can reason about documents it never read."

---

## 1:40–2:40 — Extraction

**Show:** terminal. Run:

```bash
python -m loupe.cli extract
```

*(This will say everything is already processed — that's the point.)*

> "First, extraction. Every document gets read and turned into typed claims — atomic facts, each one bound to an exact page and character range.
>
> Notice it says everything's already processed. That's the checkpointing: if a run gets interrupted, it resumes rather than starting over. That happened to me for real during development when I hit a rate limit.
>
> Sixty-one claims from ten documents."

**Show:** run this to display the entity grouping:

```bash
python -c "
from pathlib import Path
from loupe.store import EvidenceStore
s = EvidenceStore(Path('data/run'))
s.load()
t = s.claims_about('TitanRetail Group')
print(f'{len(t)} claims across {sorted({c.document_id for c in t})}')
"
```

> "And here's the piece that makes the whole thing work. Claims about TitanRetail — four of them, and look at the source documents. The contract and the financial statements. Both under one key.
>
> The extractor originally produced 'TitanRetail Group' and 'TitanRetail Group Limited' as two separate entities, which meant those claims never got compared. Twenty lines of name normalisation fixed it. Without that, the finding I'm about to show you is unreachable."

---

## 2:40–4:00 — Detection

**Show:** terminal. Run:

```bash
python -m loupe.cli detect --fresh --no-approval
```

> "Now detection. This runs four detectors over the claim graph.
>
> Arithmetic first — pure Python, no model. It reconciles the cap table.
>
> Then the gap audit, which reports documents that should be there and aren't.
>
> Then the tension detector — this is the language model agent. It takes every claim about one company, from whichever documents they came from, and asks a very specific question: what conflicts here? Not 'find risks' — if you ask a model to find risks it will find them whether or not they exist. 'What conflicts' has a wrong answer. It either points at two specific claims or it returns nothing.
>
> Six entities analysed. Five came back with nothing. One came back with the finding."

**Pause on the output.** Point at the TitanRetail finding.

> "There it is. Critical severity. Cross-document. And look at the citations — one from the contract, one from the financial statements. Exact quotes, exact pages.
>
> That's a conclusion neither document supports on its own."

---

## 4:00–4:50 — Adversarial review

**Show:** scroll to the review section of the output.

> "Before anything gets reported, every finding goes through a red team critic.
>
> The critic isn't asked to review findings. It's asked to destroy them — construct the strongest possible argument that each one is wrong. If you ask a model 'is this correct?', it agrees, because agreeing is the easy path. If you tell it to attack, it actually attacks.
>
> Here it retracted two findings. It argued that a litigation schedule isn't a document companies keep in the ordinary course — it's drafted during the transaction — so its absence isn't a red flag. That's correct, and I hadn't thought of it.
>
> And this is enforced by the type system, not by convention. Calling confirm on a finding that was never challenged raises an exception. There's no code path that gets a finding into the report without review."

---

## 4:50–5:40 — The memo

**Show:** open `data/memo.md` after running:

```bash
python -m loupe.cli memo
```

> "The output is an investment committee memo.
>
> Every finding has its evidence quoted with a document and page reference. Every finding shows what the critic argued against it, and notes that it was reported anyway — so a reader can see the objection that was overcome, not just the conclusion.
>
> There's a section listing documents to request from the seller. And here at the bottom, findings that were considered and withdrawn, with the reasons. Most AI systems only show you what they concluded. This one shows you what it considered and rejected.
>
> The memo is generated deterministically. No model is involved in writing it — it's a rendering of the findings ledger, so it can't hallucinate and it can't change between runs."

---

## 5:40–6:20 — The score

**Show:** terminal. Run:

```bash
python -m loupe.cli score
```

> "The last piece is the one I care most about.
>
> I generated the corpus myself, so I know exactly what's wrong with it and where. Three defects planted at known locations — an arithmetic discrepancy, the cross-document liability, and a missing document.
>
> Three out of three detected. Zero findings that correspond to nothing real.
>
> I want to be honest about the caveat: ten documents is enough to demonstrate the mechanism, not enough to characterise performance. The meaningful result is the cross-document defect, because that one needed evidence from two documents that no single reader would have compared."

---

## 6:20–7:00 — Close

**Show:** the terminal, or slide 10 of your deck.

> "One last thing, because it's the best evidence the design works.
>
> My arithmetic detector originally summed founder shares, preferred shares, and employee options against the cap table total. All my tests passed. Three days of green.
>
> The critic retracted it. It said adding unexercised options to issued and outstanding shares is a definitional error — options aren't issued shares until someone exercises them.
>
> It was right. My detector, my test corpus, and my test were all wrong in the same way, so my tests could never have caught it. An adversarial agent caught a domain error in my own reasoning.
>
> I corrected it. The real defect is 350,000 shares stated as outstanding with no identified holder — which is subtler and more realistic than the one I planted.
>
> The code's on GitHub. Thanks for watching."

---

## If you're running short

Cut in this order:

1. The extraction section (2:40 mark) — mention checkpointing verbally instead of showing it
2. The memo walkthrough — show it for ten seconds rather than reading sections
3. The architecture explanation at 0:50 — compress to two sentences

**Never cut:** the opening problem, the TitanRetail finding, the score, or the critic-caught-my-mistake close. Those four carry the video.

## If you're running long

The problem setup at the start tends to expand. Practise it once with a timer — aim to be at the 50-second mark when you say "that's what this system is built to catch."
