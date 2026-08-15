"""Employment documents for Northwind Analytics Inc.

Carries planted defects D-004 (option grants do not reconcile to the cap
table), D-006 (CFO salary contradicts the board resolution), D-011 (a board
consent referenced but absent), D-014 and D-015 (undisclosed relationships
via shared addresses).

Home addresses are included because that is how an undisclosed related-party
relationship actually surfaces in diligence: the same address appearing on a
founder's employment agreement and a supplier's registration.
"""

from __future__ import annotations

from loupe.corpus.spec import DocSpec

CEO_EMPLOYMENT = DocSpec(
    filename="employment_ceo.docx",
    doc_type="employment_agreement",
    title="Executive Employment Agreement - Sarah Chen",
    paragraphs=(
        "This Employment Agreement is made on 19 June 2019 between Northwind "
        "Analytics Inc. and Sarah Chen, residing at 44 Lakeshore Drive, "
        "Portland, Oregon.",
        "Position. The Executive shall serve as Chief Executive Officer.",
        "Compensation. The Executive shall receive an annual base salary of "
        "USD 240,000, subject to annual review by the Board.",
        "Equity. The Executive holds 1,800,000 shares of common stock subject "
        "to a four year vesting schedule commencing on the date of this "
        "Agreement.",
        "Termination. Either party may terminate this Agreement on ninety "
        "(90) days written notice.",
    ),
)

CTO_EMPLOYMENT = DocSpec(
    filename="employment_cto.docx",
    doc_type="employment_agreement",
    title="Executive Employment Agreement - David Okonkwo",
    paragraphs=(
        "This Employment Agreement is made on 19 June 2019 between Northwind "
        "Analytics Inc. and David Okonkwo, residing at 210 Cedar Street, "
        "Portland, Oregon.",
        "Position. The Executive shall serve as Chief Technology Officer.",
        "Compensation. The Executive shall receive an annual base salary of "
        "USD 225,000, subject to annual review by the Board.",
        "Equity. The Executive holds 1,200,000 shares of common stock subject "
        "to a four year vesting schedule commencing on the date of this "
        "Agreement.",
    ),
)

CFO_EMPLOYMENT = DocSpec(
    filename="employment_cfo.docx",
    doc_type="employment_agreement",
    title="Executive Employment Agreement - Priya Raghunathan",
    paragraphs=(
        "This Employment Agreement is made on 16 September 2024 between "
        "Northwind Analytics Inc. and Priya Raghunathan, residing at 88 "
        "Alder Way, Seattle, Washington.",
        "Position. The Executive shall serve as Chief Financial Officer, as "
        "approved by written consent of the Board of Directors dated "
        "9 September 2024.",
        "Compensation. The Executive shall receive an annual base salary of "
        "USD 260,000, subject to annual review by the Board.",
        "Equity. The Executive shall be granted options over 120,000 shares "
        "of common stock, vesting over four years.",
        "Termination. Either party may terminate this Agreement on sixty "
        "(60) days written notice.",
    ),
)

OPTION_GRANTS = DocSpec(
    filename="option_grant_schedule.docx",
    doc_type="cap_table",
    title="Employee Option Grant Schedule - as at 31 December 2025",
    paragraphs=(
        "This schedule records all option grants made to employees and "
        "outstanding at the date shown.",
        "Priya Raghunathan, Chief Financial Officer: 120,000 options granted "
        "16 September 2024.",
        "Marcus Ferrell, VP Engineering: 95,000 options granted 3 May 2023.",
        "Anneke Vos, VP Sales: 80,000 options granted 12 October 2023.",
        "Tomas Berg, Head of Product: 75,000 options granted 1 February 2024.",
        "Leila Haddad, Head of Customer Success: 45,000 options granted "
        "20 June 2024.",
        "Eleven other employees hold grants totalling 30,000 options in "
        "aggregate.",
    ),
)

DEVSHOP_CONTRACTOR = DocSpec(
    filename="contractor_agreement_devshop.docx",
    doc_type="contract",
    title="Independent Contractor Agreement - Cedar Devshop LLC",
    paragraphs=(
        "This Independent Contractor Agreement is made on 1 March 2025 "
        "between Northwind Analytics Inc. and Cedar Devshop LLC, whose "
        "principal is S. Okonkwo and whose registered address is 210 Cedar "
        "Street, Portland, Oregon.",
        "Scope. Contractor shall provide software engineering services "
        "relating to the analytics engine and associated data pipelines.",
        "Fees. Customer shall pay USD 18,000 per month for the duration of "
        "the engagement.",
        "Intellectual property. All work product created by Contractor is "
        "assigned to the Company, such assignment being effective from "
        "1 March 2025.",
        "Term. This Agreement continues until terminated by either party on "
        "thirty (30) days written notice.",
    ),
)

SEVERANCE_POLICY = DocSpec(
    filename="severance_policy.docx",
    doc_type="other",
    title="Executive Severance Policy - Northwind Analytics Inc.",
    paragraphs=(
        "This policy was adopted by the Board on 4 September 2024 and applies "
        "to executive officers of the company.",
        "On termination without cause, an executive officer is entitled to "
        "twelve (12) months of base salary paid as severance.",
        "On a change of control of the company followed by termination "
        "without cause within twelve months, an executive officer is "
        "entitled to eighteen (18) months of base salary and full "
        "acceleration of unvested equity.",
        "This policy may be amended by the Board at any time, save that no "
        "amendment shall reduce an entitlement that has already accrued.",
    ),
)

EMPLOYMENT_DOCUMENTS: tuple[DocSpec, ...] = (
    CEO_EMPLOYMENT,
    CTO_EMPLOYMENT,
    CFO_EMPLOYMENT,
    OPTION_GRANTS,
    DEVSHOP_CONTRACTOR,
    SEVERANCE_POLICY,
)
