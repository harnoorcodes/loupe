"""Financial documents for Northwind Analytics Inc.

Carries or supports planted defects D-002 (revenue concentration),
D-005 (revenue schedule does not sum to stated total), D-007 (deferred
revenue contradiction), D-008 (revenue ignores an amended fee),
D-009 (loan acceleration against available cash) and D-013 (IP created
before its assignment took effect).
"""

from __future__ import annotations

from loupe.corpus.spec import DocSpec

FINANCIALS_2025 = DocSpec(
    filename="financial_statements_2025.pdf",
    doc_type="financial_statement",
    title="Northwind Analytics Inc. - Financial Statements FY2025 (unaudited)",
    paragraphs=(
        "Total revenue for the financial year ended 31 December 2025 was "
        "USD 8,400,000, an increase of 34% over the prior year.",
        "Revenue is recognised rateably over the subscription term in "
        "accordance with the company's stated accounting policy.",
        "Customer concentration: TitanRetail Group accounted for "
        "USD 3,612,000 of revenue in FY2025, representing 43% of total "
        "revenue.",
        "The next largest customers were Meridian Logistics at "
        "USD 1,008,000 and Bluepeak Health at USD 756,000.",
        "Deferred revenue as at 31 December 2025 was USD 2,100,000.",
        "Cash and cash equivalents at year end totalled USD 1,940,000.",
        "Borrowings comprise a term loan facility with Meridian Bank with "
        "USD 3,000,000 outstanding at year end.",
    ),
)

FINANCIALS_2024 = DocSpec(
    filename="financial_statements_2024.pdf",
    doc_type="financial_statement",
    title="Northwind Analytics Inc. - Financial Statements FY2024 (unaudited)",
    paragraphs=(
        "Total revenue for the financial year ended 31 December 2024 was "
        "USD 6,270,000.",
        "Customer concentration: TitanRetail Group accounted for "
        "USD 2,408,000 of revenue in FY2024, representing 38% of total "
        "revenue.",
        "Deferred revenue as at 31 December 2024 was USD 1,480,000.",
        "Cash and cash equivalents at year end totalled USD 2,610,000.",
        "The company had no borrowings outstanding at 31 December 2024.",
    ),
)

REVENUE_BY_CUSTOMER = DocSpec(
    filename="revenue_by_customer_2025.pdf",
    doc_type="financial_statement",
    title="Revenue by Customer - FY2025 - Northwind Analytics Inc.",
    paragraphs=(
        "This schedule sets out recognised revenue by customer for the "
        "financial year ended 31 December 2025.",
        "TitanRetail Group: USD 3,612,000.",
        "NovaClear GmbH: USD 1,344,000.",
        "Meridian Logistics BV: USD 1,008,000.",
        "Pacifica Systems Pte Ltd: USD 890,000.",
        "Bluepeak Health: USD 756,000.",
        "All other customers in aggregate: USD 1,000,000.",
    ),
)

DEFERRED_REVENUE = DocSpec(
    filename="deferred_revenue_schedule.pdf",
    doc_type="financial_statement",
    title="Deferred Revenue Schedule - as at 31 December 2025",
    paragraphs=(
        "This schedule reconciles amounts invoiced but not yet recognised as "
        "revenue at the balance sheet date.",
        "Total deferred revenue as at 31 December 2025 is USD 2,340,000.",
        "Of that amount, USD 1,025,000 relates to TitanRetail Group and is "
        "expected to be recognised during the first three quarters of 2026.",
        "USD 615,000 relates to NovaClear GmbH under an annual prepayment "
        "received in June 2025.",
        "The balance relates to a range of smaller subscription customers.",
    ),
)

RECEIVABLES_AGEING = DocSpec(
    filename="receivables_ageing_2025.pdf",
    doc_type="financial_statement",
    title="Accounts Receivable Ageing - as at 31 December 2025",
    paragraphs=(
        "Total trade receivables outstanding at 31 December 2025 were "
        "USD 1,180,000.",
        "Amounts current and not yet due: USD 742,000.",
        "Amounts overdue between 31 and 60 days: USD 218,000.",
        "Amounts overdue between 61 and 90 days: USD 145,000.",
        "Amounts overdue by more than 90 days: USD 75,000, of which "
        "USD 61,000 is owed by a single customer and is the subject of "
        "ongoing collection correspondence.",
    ),
)

LOAN_AGREEMENT = DocSpec(
    filename="loan_agreement_meridian_bank.pdf",
    doc_type="contract",
    title="Term Loan Agreement - Meridian Bank and Northwind Analytics Inc.",
    paragraphs=(
        "This Term Loan Agreement is dated 20 September 2024 between "
        "Meridian Bank NA as lender and Northwind Analytics Inc. as "
        "borrower.",
        "Section 2. Facility. The lender makes available a term loan facility "
        "in the principal amount of USD 3,000,000.",
        "Section 5. Interest. Interest accrues at a rate of eight and one "
        "half percent (8.5%) per annum, payable quarterly.",
        "Section 9. Repayment. The principal is repayable in full on "
        "20 September 2029 unless accelerated in accordance with Section 14.",
        "Section 14. Acceleration on change of control. If the borrower "
        "undergoes a change of control, including any transfer of more than "
        "fifty percent (50%) of its voting securities, the entire "
        "outstanding principal together with accrued interest becomes "
        "immediately due and payable at the lender's election.",
        "Section 16. Financial covenant. The borrower shall maintain "
        "unrestricted cash of not less than USD 1,500,000 at all times.",
    ),
)

MANAGEMENT_ACCOUNTS = DocSpec(
    filename="management_accounts_q1_2026.pdf",
    doc_type="financial_statement",
    title="Management Accounts - Quarter Ended 31 March 2026",
    paragraphs=(
        "Revenue for the quarter was USD 2,310,000, ahead of the internal "
        "plan of USD 2,180,000.",
        "Engineering costs include the final instalment for the analytics "
        "engine rewrite, which was delivered by external contractors in "
        "November 2024 and capitalised over the following periods.",
        "Cash at 31 March 2026 stood at USD 1,620,000 following the "
        "quarterly interest payment on the Meridian Bank facility.",
        "Headcount at quarter end was 34 full time employees and 6 "
        "contractors.",
        "Management notes that the largest customer relationship remains "
        "under negotiation for renewal.",
    ),
)

FINANCIAL_DOCUMENTS: tuple[DocSpec, ...] = (
    FINANCIALS_2025,
    FINANCIALS_2024,
    REVENUE_BY_CUSTOMER,
    DEFERRED_REVENUE,
    RECEIVABLES_AGEING,
    LOAN_AGREEMENT,
    MANAGEMENT_ACCOUNTS,
)
