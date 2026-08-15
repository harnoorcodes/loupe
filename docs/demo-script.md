# Demo video script

**Target length:** 8 minutes (assignment allows 5–10)
**Format:** screen recording with voiceover, driven by the web interface
**Tool:** OBS Studio, Loom, or Windows Game Bar (`Win + G`)

The interface carries the demo. The terminal appears twice and briefly.

---

## Before you record

### Warm the cache

Every model call must be cached so the recorded run completes in seconds with no network dependency.

```bash
python -m loupe.cli detect --fresh --no-approval
python -m loupe.cli ablate
```

Then start the server:

```bash
python -m loupe.web.app
```

Open **http://127.0.0.1:8000** and click **"Use the sample data room"** once, all the way through. That warms the web path specifically. Then reload the page so you start clean.

### Checklist

- [ ] Browser at 100% zoom, window maximised, bookmarks bar hidden
- [ ] Notifications silenced, second monitor for this script
- [ ] These two PDFs open in separate tabs for the opening: `data/synthetic/contract_titanretail.pdf` and `data/synthetic/financial_statements_2025.pdf`
- [ ] Terminal open in a second window, font enlarged, for the two moments it appears
- [ ] Microphone tested

**Record in one take if you can.** Small stumbles read as authentic. A heavily edited video reads as rehearsed.

---

## 0:00–0:55 — The problem, in two documents

**Show:** the two PDFs side by side, scrolled to the relevant clauses.

> "When one company buys another, the buyer gets a few weeks to read several hundred documents. I want to show you the kind of thing that gets missed.
>
> This is a customer contract. Section 11 — change of control. If the supplier is acquired, this customer can walk away on thirty days notice, no penalty.
>
> [switch tabs]
>
> And this is the financial statement. That same customer, TitanRetail, is 43% of total revenue.
>
> Neither document is alarming on its own. The lawyer reads the first, the accountant reads the second, and they work in different rooms — so nobody puts them together. The buyer finds out after closing that they've destroyed nearly half the revenue they paid for.
>
> This is Loupe. It's built to catch exactly that."

---

## 0:55–1:35 — The interface, and what it's about to do

**Show:** the landing page. Let the hero text sit on screen for a beat.

> "Ten agents, built on the OpenAI Agents SDK, running on Gemini. Six of them use a language model. Six are plain Python — because reconciling a share total is arithmetic, not judgement, and Python is faster, free, and right every time.
>
> I'm going to run it against a data room I generated myself. Thirty-five documents for a fictional company, with fifteen problems deliberately hidden inside — and I know exactly where all fifteen are, because I put them there.
>
> That last part is what makes this measurable rather than impressive-looking."

**Click "Use the sample data room."**

---

## 1:35–2:30 — Watch it run

**Show:** the progress panel. Let the stages tick.

> "Here's the pipeline. It classifies each document by reading it, not by guessing from the filename. Extracts every factual claim with an exact page and character reference. Then four detectors run — three of them with no model at all.
>
> Then targeted pair analysis, then adversarial review, then materiality scoring.
>
> Notice the timings on the right. This whole run is cached, so it's finishing in a couple of seconds. That's deliberate — a demo that depends on live API calls is a demo that can fail in front of an audience. It also means the results are reproducible instead of varying with model sampling."

*If it finishes before you've said all that, keep talking over the findings page. Don't rush the point about reproducibility.*

---

## 2:30–3:30 — The findings

**Show:** the findings page. Point at the stat cards.

> "Seven of the fifteen planted defects found. Two hundred and thirty-two claims extracted. Zero findings that correspond to nothing real.
>
> I'll come back to that seven, because I want to be honest about the eight it missed.
>
> Here are the findings, sorted by severity."

**Scroll to the TitanRetail finding.**

> "This is the one I showed you at the start. Look at the badges — cross-document, latent liability. And the two citations underneath: one from the contract, one from the financial statements.
>
> That's a conclusion neither document supports on its own."

---

## 3:30–4:30 — The citation click ★

**This is the most important thirty seconds of the video. Slow down.**

**Click the `contract_titanretail p.1` citation.**

> "And this is the part that matters most to me.
>
> The source document opens right there, at the cited page, with the exact quoted text above it. One click.
>
> The reason that's the centrepiece rather than a nice touch: an analyst's only way to check any finding is to follow the citation. If one of them is wrong, they stop trusting all of them — and they'd be right to.
>
> So the system is built so it structurally cannot invent one. The model is never asked for character positions. It returns the exact text it's quoting, and the system finds that text itself with a string search. If the quote doesn't exist in the document, the claim is thrown away rather than reported with a broken reference."

**Click the second citation** — `financial_statements_2025 p.1` — so the panel switches documents.

> "Second citation, different document, same finding. That's the cross-document part made literal."

**Press Escape to close.**

---

## 4:30–5:15 — Adversarial review

**Show:** scroll down within a finding to the objection block.

> "Before anything gets reported, every finding goes through an agent whose only job is to destroy it.
>
> Not review it — destroy it. If you ask a model 'is this correct?', it agrees, because agreeing is the easy path. If you tell it to construct the strongest possible argument that the finding is wrong, it actually tries.
>
> Here's what it argued against this one. The finding was reported anyway, because the objection wasn't strong enough. But you can see what was argued, which means you're seeing the reasoning rather than just the conclusion."

**Scroll to the "Considered and withdrawn" section.**

> "And here are the findings it killed. Most of these are duplicates — the same issue raised twice by different detectors. The critic sees all findings at once, so it catches that.
>
> This is also enforced by the type system, not by convention. Calling confirm on a finding that was never challenged raises an exception. There's no code path that gets an unreviewed finding into the report."

---

## 5:15–6:30 — The evaluation tab ★

**Click "Evaluation" in the left rail.**

> "Now the part I care about most.
>
> Seven of fifteen. Forty-seven percent. Zero noise.
>
> Most projects in this space can't tell you whether their output is correct. Because I generated the corpus, I know exactly what's wrong with it — so this is measured, not claimed."

**Scroll to the by-class table.**

> "Broken down by the kind of problem. Undisclosed relationships, two out of two. Temporal impossibilities, zero out of two — that detector runs and never fires, and I know why."

**Scroll to the per-defect table.**

> "And this is the table that makes the whole thing worth building. Every planted defect, with the specific capability its detection depends on.
>
> Four of these were designed to be beyond the system — they need version handling, or a three-document reasoning chain, or coreference resolution. Two of them got caught anyway, by a route I didn't predict.
>
> This isn't a list of excuses. It's a prioritised engineering backlog derived from measurement instead of guesswork. If I had a clean fifteen out of fifteen, I'd have learned nothing."

---

## 6:30–7:20 — The ablation study ★

**Switch to the terminal.**

```bash
python -m loupe.cli ablate
```

*(Fully cached — completes in seconds.)*

> "Last thing, and it's the piece I'd point at in an interview.
>
> This removes one component at a time and re-scores. It turns claims about the architecture into measurements."

**Point at the table as it appears.**

> "Remove the pair detector: seven drops to three. That component is doing more than half the work.
>
> Remove adversarial review: recall goes *up* to eight — and noise goes from zero to forty-four percent. Sixteen findings instead of eight, and seven of the extra ones are meaningless.
>
> That's the precision-recall tradeoff with an actual number on it. For a diligence report, precision is the side that matters — an analyst who hits seven false findings stops reading, and then your recall is zero regardless of what it measured.
>
> And this row: removing the entity-grouped tension detector changes nothing. That's a component I built that earns no cost. I'm reporting it because it's exactly the kind of result you don't go looking for in your own system."

---

## 7:20–8:00 — Close

**Switch back to the browser, findings page.**

> "One last thing, because it's the best evidence the design works.
>
> My arithmetic detector originally summed founder shares, preferred shares, and employee options against the cap table total. All my tests passed. Three days of green.
>
> The critic retracted it. It said adding unexercised options to issued and outstanding shares is a definitional error — options aren't issued shares until someone exercises them.
>
> It was right. My detector, my test corpus, and my test were all wrong in the same way, so my tests could never have caught it. An adversarial agent caught a domain error in my own reasoning.
>
> I corrected it. The real defect is 350,000 shares outstanding with no identified holder, which is subtler and more realistic than the one I planted.
>
> The code's on GitHub, with the full evaluation and the ablation results. Thanks for watching."

---

## Timing guide

| Section | Duration | Cumulative |
| --- | --- | --- |
| Problem in two documents | 0:55 | 0:55 |
| Interface and setup | 0:40 | 1:35 |
| Watching it run | 0:55 | 2:30 |
| The findings | 1:00 | 3:30 |
| **Citation click** | 1:00 | 4:30 |
| Adversarial review | 0:45 | 5:15 |
| **Evaluation tab** | 1:15 | 6:30 |
| **Ablation study** | 0:50 | 7:20 |
| Close | 0:40 | 8:00 |

---

## If you run long

Cut in this order:

1. The "Considered and withdrawn" section — mention it verbally instead
2. The second citation click — one is enough to make the point
3. The by-class table on the evaluation tab — go straight to the per-defect table

**Never cut:** the opening two documents, the citation click, the evaluation tab, the ablation table, or the closing story about the critic catching your error. Those five carry the video.

## If you run short

Two things worth adding:

- **The documents tab** — showing the classifier reassigned types by reading the text rather than trusting filenames.
- **The pairs command** in the terminal: `python -m loupe.cli pairs`. It shows the candidate pairs with zero model calls, which demonstrates that retrieval is deterministic and inspectable before any money is spent.

## Delivery notes

- **The citation click is the emotional centre.** Pause after the document opens. Let it land before you explain it.
- **Say the honest numbers out loud.** "Seven of fifteen" spoken confidently is more persuasive than fifteen of fifteen, because it tells the viewer you measured rather than tuned.
- **Don't apologise for the misses.** Frame the per-defect table as a backlog, not a shortfall. It is one.
- **Practise the opening once with a timer.** Aim to be at the 55-second mark when you say "this is Loupe."
