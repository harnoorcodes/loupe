# Due Diligence Findings — Northwind Analytics Inc.

Generated 13 August 2026 by Loupe.

---

## Summary

6 confirmed findings: 4 high, 1 medium, 1 low. 2 of these required evidence from more than one document.

Reviewed 10 documents and extracted 61 claims. Every finding below was challenged by an adversarial reviewing agent before being reported, and every citation was verified against its source document.

---

## Findings

### 1. Missing: Shareholders Agreement

**Severity:** High  
**Type:** missing document  
**Scope:** single document  
**Raised by:** gap_auditor

No document satisfying this request was found in the data room. Governs transfer restrictions, drag-along and tag-along rights, any of which can block or complicate a sale.

**Evidence**

- None. This finding concerns a document that is absent from the data room.

**Adversarial review**

The reviewing agent argued: _A Shareholders Agreement is only required if there are multiple shareholders wishing to govern their relationship; if the company is closely held or has simple governance, one might not exist._

The finding was reported notwithstanding that objection.

### 2. Missing: Equity incentive plan document

**Severity:** High  
**Type:** missing document  
**Scope:** single document  
**Raised by:** gap_auditor

No document satisfying this request was found in the data room. This document is required because the corpus states: "410,000 options have been granted to employees". Options granted without an adopted plan may be invalid, leaving the company exposed to claims from holders and the cap table materially misstated.

**Evidence**

- None. This finding concerns a document that is absent from the data room.

**Adversarial review**

The reviewing agent argued: _The company may grant options on an ad-hoc basis through individual option agreements approved by the Board of Directors without having formally adopted a comprehensive equity incentive plan._

The finding was reported notwithstanding that objection.

### 3. Missing: Tax returns for the last three years

**Severity:** High  
**Type:** missing document  
**Scope:** single document  
**Raised by:** gap_auditor

No document satisfying this request was found in the data room. Unpaid or disputed tax transfers to the buyer.

**Evidence**

- None. This finding concerns a document that is absent from the data room.

**Adversarial review**

The reviewing agent argued: _Tax returns might be temporarily unavailable or the company may be a newly formed entity that has not yet filed three years of returns._

The finding was reported notwithstanding that objection.

### 4. Customer with Change of Control termination represents 43% of total revenue

**Severity:** High  
**Type:** latent liability  
**Scope:** cross-document  
**Raised by:** tension_detector

According to the contract, TitanRetail Group can terminate its agreement upon 30 days notice in the event of a change of control. Financial statements indicate that TitanRetail Group accounts for 43% of the total revenue. A change of control event during a merger could trigger this termination right, risking the loss of a major revenue streams that represents nearly half of the target's total revenue.

**Evidence**

- `contract_titanretail p.1` — "upon thirty (30) days written notice"
- `financial_statements_2025 p.1` — "representing 43% of total revenue"

**Adversarial review**

The reviewing agent argued: _The cited evidence of 'upon thirty (30) days written notice' indicates a standard termination for convenience rather than a specific change-of-control provision. Furthermore, the financial statement data is listed as 'conflicting' when it is actually supporting evidence._

The finding was reported notwithstanding that objection.

### 5. Stated share total does not reconcile with identified holdings

**Severity:** Medium  
**Type:** arithmetic  
**Scope:** cross-document  
**Raised by:** arithmetic_detector

The cap table states 4,250,000 shares issued and outstanding, but identified holdings account for only 3,900,000 (1,800,000 + 1,200,000 + 900,000). 350,000 shares are unaccounted for against the identified holdings. Either a holder is undisclosed or the stated total is wrong; in either case the buyer cannot rely on the stated ownership percentages. Unexercised options are excluded from this reconciliation, as they are not issued shares.

**Evidence**

- `cap_table p.1` — "Total issued and outstanding shares: 4,250,000."
- `cap_table p.1` — "Sarah Chen holds 1,800,000 common shares."
- `employment_cto p.1` — "The Executive holds 1,200,000 shares of common stock"
- `cap_table p.1` — "Kestrel Ventures LP holds 900,000 preferred shares"

**Adversarial review**

The reviewing agent argued: _The 350,000 share difference is highly likely to be held by undisclosed minority shareholders (such as employees or early-stage angel investors) who are not highlighted on page 1 of the cap table, rather than representing an arithmetic error or invalid cap table._

The finding was reported notwithstanding that objection.

### 6. Missing: Accounts receivable ageing schedule

**Severity:** Low  
**Type:** missing document  
**Scope:** single document  
**Raised by:** gap_auditor

No document satisfying this request was found in the data room. Reveals collection risk that headline revenue figures conceal.

**Evidence**

- None. This finding concerns a document that is absent from the data room.

**Adversarial review**

The reviewing agent argued: _An accounts receivable aging schedule is a routine working capital document, and its absence represents a standard financial diligence request rather than a major transaction risk._

The finding was reported notwithstanding that objection.

---

## Documents to request from the seller

The following were expected but not provided.

- Shareholders Agreement
- Equity incentive plan document
- Tax returns for the last three years
- Accounts receivable ageing schedule

---

## Findings considered and withdrawn

These were proposed by a detector and then withdrawn during adversarial review. They are listed so the reader can see what was considered, not only what was reported.

**Missing: Litigation schedule or no-litigation confirmation**

Withdrawn because: The objection is correct. A company does not maintain a 'no-litigation confirmation' in the ordinary course of business. This is a transaction-specific disclosure drafted during the contract negotiation phase, making its 'absence' from the VDR a non-issue.

**Missing: Debt agreements and loan documentation**

Withdrawn because: If the company is debt-free, no such agreements exist. Without any evidence of outstanding debt in the company's financial statements, claiming these documents are 'missing' is speculative and unsupported.

---

## Method and limitations

Claims were extracted from every document with a page and character reference. Contradictions were detected by comparing claims about the same entity drawn from different documents. Absent documents were identified by comparing the corpus against a standard diligence request list.

This report identifies issues for human review. It does not provide legal advice, does not value the business, and does not recommend whether to proceed.
