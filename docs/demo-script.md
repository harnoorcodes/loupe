# Demo video script

**Target length:** 8.5 minutes (assignment allows 5–10)
**Format:** screen recording with voiceover, driven by the web interface
**Tool:** OBS Studio, Loom, or Windows Game Bar (`Win + G`)

The interface carries the demo. The terminal appears once, briefly.

---

## Before you record

### Warm the cache

Every model call must be cached so the recorded run completes in seconds with no network dependency.

```bash
python -m loupe.cli detect --fresh --no-approval
python -m loupe.cli ablate
python -m loupe.web.app
```

Open http://127.0.0.1:8000, click **"Use the sample data room"**, let it finish, then reload the page so you start clean.

**Confirm it shows 7/15.** If it shows something else, that number is what you narrate — the script says seven throughout, so adjust as you go rather than re-running to chase it.

### Checklist

- [ ] Browser at 100% zoom, window maximised, bookmarks bar hidden
- [ ] Notifications silenced, second monitor or printout for this script
- [ ] Two PDFs open in tabs for the opening: `data/synthetic/contract_titanretail.pdf` and `data/synthetic/financial_statements_2025.pdf`
- [ ] Terminal open in a second window, font enlarged, for the ablation
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

## 0:55–1:35 — What it is

**Show:** the landing page. Let the hero text sit for a beat.

> "Thirteen agents, built on the OpenAI Agents SDK, running on Gemini. Six of them use a language model. Seven are plain Python — because reconciling a share total is arithmetic, not judgement, and Python is faster, free, and right every time.
>
> I'm going to run it against a data room I generated myself. Thirty-five documents for a fictional company, with fifteen problems deliberately hidden inside — and I know exactly where all fifteen are, because I put them there.
>
> That last part is what makes this measurable rather than impressive-looking."

**Click "Use the sample data room."**

---

## 1:35–2:20 — Watch it run

**Show:** the progress panel.

> "It classifies each document by reading it, not by guessing from the filename. Extracts every factual claim with an exact page and character reference. Then five detectors run — four of them with no model at all.
>
> Then targeted pair analysis, adversarial review, and materiality scoring.
>
> Notice the timings. This whole run is cached, so it's finishing in under a second. That's deliberate — a demo that depends on live API calls is a demo that can fail in front of an audience. It also means the results are reproducible instead of varying with model sampling, and I'll come back to why that matters."

---

## 2:20–3:20 — The findings

**Show:** the findings page. Point at the stat cards.

> "Seven of the fifteen planted defects found. Two hundred and thirty-two claims extracted. One finding in nine that doesn't correspond to anything real.
>
> I'll come back to that seven, because I want to be honest about the eight it missed.
>
> Here's the top finding. The cap table says four and a quarter million shares issued and outstanding. Identified holdings account for only three point nine million. Three hundred and fifty thousand shares with nobody named as holding them."

**Point at the citations.**

> "Three citations. And look at the third one — that's from the CTO's employment agreement, not the cap table. The system pulled a shareholding out of an employment contract to check a cap table.
>
> That's the cross-document part, and it's the whole reason the architecture looks the way it does."

---

## 3:20–4:20 — The citation click ★

**This is the most important minute of the video. Slow down.**

**Click the `cap_table p.1` citation.**

> "And this is the part that matters most to me.
>
> The source document opens right there, at the cited page, with the exact quoted text above it. One click.
>
> The reason that's the centrepiece rather than a nice touch: an analyst's only way to check any finding is to follow the citation. If one of them is wrong, they stop trusting all of them — and they'd be right to.
>
> So the system is built so it structurally cannot invent one. The model is never asked for character positions. It returns the exact text it's quoting, and the system finds that text itself with a string search. If the quote doesn't exist in the document, the claim is thrown away rather than reported with a broken reference."

**Click the `employment_cto p.1` citation** so the panel switches documents.

> "Different citation, different document, same finding. That's what cross-document verification looks like in practice."

**Press Escape.**

---

## 4:20–4:55 — Adversarial review

**Show:** scroll to the objection block inside a finding.

> "Before anything gets reported, every finding goes through an agent whose only job is to destroy it.
>
> Not review it — destroy it. Ask a model 'is this correct?' and it agrees, because agreeing is the easy path. Tell it to construct the strongest possible argument that the finding is wrong, and it actually tries.
>
> Here's what it argued against this one. The finding was reported anyway, because the objection wasn't strong enough — but you can see the reasoning, not just the conclusion.
>
> Further down there's a section listing what it killed. And this is enforced by the type system: calling confirm on a finding that was never challenged raises an exception. There's no code path that gets an unreviewed finding into the report."

---

## 4:55–6:10 — The evaluation tab ★

**Click "Evaluation" in the left rail.**

> "Now the part I care about most.
>
> Seven of fifteen. Forty-seven percent. One finding in nine matching nothing real.
>
> Most projects in this space can't tell you whether their output is correct. Because I generated the corpus, I know exactly what's wrong with it — so this is measured, not claimed."

**Scroll to the by-class table.**

> "By kind of problem. Both negative-space classes are two out of two — reporting what a data room *doesn't* contain works reliably. Latent liability is zero out of three on this run."

**Scroll to the per-defect table.**

> "And this is the table that makes the whole thing worth building. Every planted defect, with the specific capability its detection depends on.
>
> Four of these were designed to be beyond the system — they need version handling, or a three-document reasoning chain, or coreference resolution. One got caught anyway, by a route I didn't predict."

**Point at D-011.**

> "This row is worth a second. Board consent for the CFO appointment. The CFO's employment agreement says the appointment was approved by written consent of the board dated the ninth of September. There is no such document in the data room.
>
> No checklist could have caught that, because the requirement came from the corpus itself. That's a second kind of negative space — not 'what should any deal have', but 'what does *this* deal claim to have'.
>
> The rest of this table isn't a list of excuses. It's a prioritised engineering backlog derived from measurement instead of guesswork. If I had a clean fifteen out of fifteen, I'd have learned nothing."

---

## 6:10–7:00 — The ablation study ★

**Switch to the terminal.**

```bash
python -m loupe.cli ablate
```

*(Fully cached — completes in seconds.)*

> "Last measurement, and it's the piece I'd point at in an interview.
>
> This removes one component at a time and re-scores. It turns claims about the architecture into numbers."

**Point at the table as it appears.**

> "Remove the pair detector: eight drops to five. That component is doing most of the work.
>
> Remove adversarial review: recall goes *up* to ten — and noise goes from zero to thirty-nine percent. Eighteen findings instead of nine, and seven of the extra ones are meaningless.
>
> That's the precision-recall tradeoff with an actual number on it. For a diligence report, precision is the side that matters — an analyst who hits seven false findings stops reading, and then your recall is zero regardless of what it measured.
>
> And this row: removing the entity-grouped tension detector changes nothing. That's a component I built that earns no cost. I'm reporting it because it's exactly the kind of result you don't go looking for in your own system."

---

## 7:00–7:25 — The variance caveat

**Stay on the terminal.**

> "One caveat I want to state rather than bury.
>
> I ran this three times over the same corpus and the same cache and got six, seven, and eight. The variance traces to a single call — the critic sometimes retracts the change-of-control finding as standard commercial practice, and sometimes doesn't.
>
> So any number here carries about plus or minus one. That isn't a bug I failed to fix; it's what LLM pipelines do. It's also why the response cache exists. Without it, this benchmark wouldn't be reproducible at all — and neither would the ablation."

---

## 7:25–8:20 — Close

**Switch back to the browser.**

> "One last thing, because it's the best evidence the design works.
>
> My arithmetic detector originally summed founder shares, preferred shares, and employee options against the cap table total. All my tests passed. Three days of green.
>
> The critic retracted it. It said adding unexercised options to issued and outstanding shares is a definitional error — options aren't issued shares until someone exercises them.
>
> It was right. My detector, my test corpus, and my test were all wrong in the same way, so my tests could never have caught it. An adversarial agent caught a domain error in my own reasoning.
>
> I corrected it. The real defect is 350,000 shares outstanding with no identified holder — subtler and more realistic than the one I planted.
>
> The code's on GitHub, with the full evaluation, the ablation results, and an honest list of the eight it still misses. Thanks for watching."

---

## Timing guide

| Section | Duration | Cumulative |
| --- | --- | --- |
| Problem in two documents | 0:55 | 0:55 |
| What it is | 0:40 | 1:35 |
| Watching it run | 0:45 | 2:20 |
| The findings | 1:00 | 3:20 |
| **Citation click** | 1:00 | 4:20 |
| Adversarial review | 0:35 | 4:55 |
| **Evaluation tab** | 1:15 | 6:10 |
| **Ablation study** | 0:50 | 7:00 |
| Variance caveat | 0:25 | 7:25 |
| Close | 0:55 | 8:20 |

---

## If you run long

Cut in this order:

1. The second citation click at 4:20 — one makes the point
2. The by-class table at 4:55 — go straight to the per-defect table
3. The adversarial review section — the objections are visible on screen anyway

**Never cut:** the opening two documents, the citation click, the per-defect table, the ablation, the variance caveat, or the closing story. Those six carry the video.

## If you run short

Two things worth adding:

- **The documents tab** — the classifier assigns type by reading, not by filename. There's a good story here: an earlier version inferred type from filenames, two schedules were typed "other", and a downstream filter silently excluded every number they contained. Two detections lost to a gap in a fallback path.
- **`python -m loupe.cli pairs`** in the terminal — shows the candidate pairs with zero model calls, demonstrating that retrieval is deterministic and inspectable before any money is spent.

## Delivery notes

- **The citation click is the emotional centre.** Pause after the document opens. Let it land before explaining it.
- **Say the honest numbers out loud.** "Seven of fifteen" spoken confidently is more persuasive than fifteen of fifteen, because it tells the viewer you measured rather than tuned.
- **Don't apologise for the misses.** Frame the per-defect table as a backlog, not a shortfall. It is one.
- **The variance section is a strength, not a confession.** Deliver it as a finding about LLM systems, which is what it is.
- **Practise the opening once with a timer.** Aim to be at the 55-second mark when you say "this is Loupe."
