"""Synthetic data room for Northwind Analytics, a fictional SaaS company.

Documents are defined as plain text here and rendered to PDF/DOCX by the
generator. Defects are planted deliberately so that recall and precision can
be measured against known ground truth.

Ground truth is recorded as SEARCH STRINGS, never character offsets. Offsets
must always be derived from extracted text after a document has been parsed,
because rendering to PDF and extracting back changes whitespace.
"""

from __future__ import annotations

from typing import NamedTuple


class DocSpec(NamedTuple):
    """A document to generate."""

    filename: str
    doc_type: str
    title: str
    paragraphs: tuple[str, ...]


class PlantedDefect(NamedTuple):
    """A defect deliberately introduced into the corpus.

    Attributes:
        defect_id: Stable identifier.
        defect_type: Matches FindingType values.
        documents: Documents that must be read together to detect it.
        anchors: Text fragments a correct finding should cite. Used to check
            whether a detected finding refers to the right evidence.
        description: What a correct finding would say.
    """

    defect_id: str
    defect_type: str
    documents: tuple[str, ...]
    anchors: tuple[str, ...]
    description: str


CAP_TABLE = DocSpec(
    filename="cap_table.pdf",
    doc_type="cap_table",
    title="Northwind Analytics Inc. - Capitalisation Table (as of 31 December 2025)",
    paragraphs=(
        "This capitalisation table reflects the issued and outstanding equity "
        "of Northwind Analytics Inc. as of 31 December 2025.",
        "Total issued and outstanding shares: 4,250,000.",
        "Founder holdings: Sarah Chen holds 1,800,000 common shares. "
        "David Okonkwo holds 1,200,000 common shares.",
        "Series A preferred: Kestrel Ventures LP holds 900,000 preferred shares "
        "issued 14 March 2024 at a price of USD 2.40 per share.",
        "Employee option grants outstanding: 410,000 options have been granted "
        "to employees under the company equity incentive plan.",
        "All shares are subject to the transfer restrictions set out in the "
        "Shareholders Agreement dated 14 March 2024.",
    ),
)

FINANCIALS = DocSpec(
    filename="financial_statements_2025.pdf",
    doc_type="financial_statement",
    title="Northwind Analytics Inc. - Financial Statements FY2025 (unaudited)",
    paragraphs=(
        "Total revenue for the financial year ended 31 December 2025 was "
        "USD 8,400,000, an increase of 34% over the prior year.",
        "Revenue is recognised rateably over the subscription term in "
        "accordance with the company's stated accounting policy.",
        "Customer concentration: TitanRetail Group accounted for USD 3,612,000 "
        "of revenue in FY2025, representing 43% of total revenue.",
        "The next largest customers were Meridian Logistics at USD 1,008,000 "
        "and Bluepeak Health at USD 756,000.",
        "Deferred revenue as at 31 December 2025 was USD 2,100,000.",
        "Cash and cash equivalents at year end totalled USD 1,940,000.",
    ),
)

TITAN_CONTRACT = DocSpec(
    filename="contract_titanretail.pdf",
    doc_type="contract",
    title="Master Subscription Agreement - TitanRetail Group",
    paragraphs=(
        "This Master Subscription Agreement is entered into on 8 May 2024 "
        "between Northwind Analytics Inc. and TitanRetail Group Limited.",
        "Section 3. Term. The initial term is thirty-six (36) months "
        "commencing on the Effective Date, renewing automatically for "
        "successive twelve (12) month periods.",
        "Section 4. Fees. Customer shall pay an annual subscription fee of "
        "USD 3,612,000 payable quarterly in advance.",
        "Section 11. Change of Control. In the event that Supplier undergoes "
        "a change of control, including any sale of substantially all of its "
        "assets or a transfer of more than fifty percent (50%) of its voting "
        "securities, Customer may terminate this Agreement upon thirty (30) "
        "days written notice without penalty or termination fee.",
        "Section 12. Assignment. Neither party may assign this Agreement "
        "without the prior written consent of the other party.",
    ),
)

MERIDIAN_CONTRACT = DocSpec(
    filename="contract_meridian.pdf",
    doc_type="contract",
    title="Master Subscription Agreement - Meridian Logistics",
    paragraphs=(
        "This Master Subscription Agreement is entered into on 2 February 2025 "
        "between Northwind Analytics Inc. and Meridian Logistics BV.",
        "Section 3. Term. The initial term is twenty-four (24) months "
        "commencing on the Effective Date.",
        "Section 4. Fees. Customer shall pay an annual subscription fee of "
        "USD 1,008,000 payable annually in advance.",
        "Section 11. Assignment. This Agreement may be assigned by either "
        "party to a successor in interest without consent.",
    ),
)

BOARD_MINUTES = DocSpec(
    filename="board_minutes_2024.pdf",
    doc_type="board_minutes",
    title="Northwind Analytics Inc. - Minutes of the Board of Directors, "
    "14 March 2024",
    paragraphs=(
        "Present: Sarah Chen (Chair), David Okonkwo, and Rachel Imani "
        "representing Kestrel Ventures LP.",
        "Resolution 1. The Board approved the issuance of 900,000 Series A "
        "preferred shares to Kestrel Ventures LP at USD 2.40 per share.",
        "Resolution 2. The Board approved the appointment of Rachel Imani as "
        "a director with effect from the date of these minutes.",
        "Resolution 3. The Board noted the intention to adopt an employee "
        "equity incentive plan and directed management to prepare a draft "
        "plan document for approval at a subsequent meeting.",
        "There being no further business, the meeting was closed.",
    ),
)

ARTICLES = DocSpec(
    filename="articles_of_incorporation.pdf",
    doc_type="corporate_charter",
    title="Articles of Incorporation - Northwind Analytics Inc.",
    paragraphs=(
        "Northwind Analytics Inc. was incorporated in the State of Delaware "
        "on 19 June 2019.",
        "The authorised capital of the corporation consists of 10,000,000 "
        "shares of common stock and 2,000,000 shares of preferred stock.",
        "The registered office of the corporation is located at 1209 Orange "
        "Street, Wilmington, Delaware.",
        "The purpose of the corporation is to engage in any lawful act or "
        "activity for which corporations may be organised under the General "
        "Corporation Law of Delaware.",
    ),
)

CEO_EMPLOYMENT = DocSpec(
    filename="employment_ceo.docx",
    doc_type="employment_agreement",
    title="Executive Employment Agreement - Sarah Chen",
    paragraphs=(
        "This Employment Agreement is made on 19 June 2019 between Northwind "
        "Analytics Inc. and Sarah Chen.",
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
        "Analytics Inc. and David Okonkwo.",
        "Position. The Executive shall serve as Chief Technology Officer.",
        "Compensation. The Executive shall receive an annual base salary of "
        "USD 225,000, subject to annual review by the Board.",
        "Equity. The Executive holds 1,200,000 shares of common stock subject "
        "to a four year vesting schedule commencing on the date of this "
        "Agreement.",
    ),
)

IP_ASSIGNMENT = DocSpec(
    filename="ip_assignment.docx",
    doc_type="other",
    title="Intellectual Property Assignment Agreement",
    paragraphs=(
        "Each of Sarah Chen and David Okonkwo hereby assigns to Northwind "
        "Analytics Inc. all right, title and interest in any intellectual "
        "property created in the course of their engagement.",
        "This assignment is effective from 19 June 2019 and covers all "
        "inventions, software, designs and works of authorship.",
    ),
)

INSURANCE = DocSpec(
    filename="insurance_policy.pdf",
    doc_type="compliance_filing",
    title="Certificate of Insurance - Northwind Analytics Inc.",
    paragraphs=(
        "Policy number NW-2025-4471 provides general liability coverage with "
        "an aggregate limit of USD 2,000,000.",
        "The policy period runs from 1 January 2025 to 31 December 2025.",
        "Directors and officers liability coverage is provided under a "
        "separate policy with an aggregate limit of USD 5,000,000.",
    ),
)

ALL_DOCUMENTS: tuple[DocSpec, ...] = (
    ARTICLES,
    CAP_TABLE,
    BOARD_MINUTES,
    FINANCIALS,
    TITAN_CONTRACT,
    MERIDIAN_CONTRACT,
    CEO_EMPLOYMENT,
    CTO_EMPLOYMENT,
    IP_ASSIGNMENT,
    INSURANCE,
)


PLANTED_DEFECTS: tuple[PlantedDefect, ...] = (
    PlantedDefect(
        defect_id="D-001",
        defect_type="arithmetic",
        documents=("cap_table.pdf",),
        anchors=(
            "Total issued and outstanding shares: 4,250,000",
            "410,000 options",
        ),
        description=(
            "Stated total of 4,250,000 shares does not reconcile with the sum "
            "of holdings: 1,800,000 + 1,200,000 + 900,000 + 410,000 = 4,310,000. "
            "Discrepancy of 60,000 shares."
        ),
    ),
    PlantedDefect(
        defect_id="D-002",
        defect_type="cross_doc_contradiction",
        documents=("contract_titanretail.pdf", "financial_statements_2025.pdf"),
        anchors=(
            "Customer may terminate this Agreement upon thirty (30) days",
            "representing 43% of total revenue",
        ),
        description=(
            "TitanRetail may terminate on change of control without penalty, "
            "and represents 43% of FY2025 revenue. An acquisition therefore "
            "puts USD 3,612,000 of annual revenue at immediate risk."
        ),
    ),
    PlantedDefect(
        defect_id="D-003",
        defect_type="missing_document",
        documents=(),
        anchors=("equity incentive plan",),
        description=(
            "410,000 options are stated as granted under an equity incentive "
            "plan, and board minutes record only an intention to prepare one. "
            "No plan document is present in the data room."
        ),
    ),
)