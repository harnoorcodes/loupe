"""Corporate documents for Northwind Analytics Inc.

Carries planted defects D-001 (share reconciliation) and supports D-006
(CFO salary contradiction) and D-011 (missing board consent).
"""

from __future__ import annotations

from loupe.corpus.spec import DocSpec

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

BYLAWS = DocSpec(
    filename="bylaws.pdf",
    doc_type="corporate_charter",
    title="Amended and Restated Bylaws - Northwind Analytics Inc.",
    paragraphs=(
        "These bylaws were adopted by the Board of Directors on 19 June 2019 "
        "and amended on 14 March 2024.",
        "Article II. The Board shall consist of not fewer than three and not "
        "more than seven directors.",
        "Article III. Any appointment of an officer of the corporation "
        "requires approval by resolution of the Board or by unanimous written "
        "consent of the directors.",
        "Article IV. Quorum for a meeting of the Board is a majority of the "
        "directors then in office.",
        "Article VII. Any issuance of equity securities requires prior "
        "approval of the Board and, where the holders of preferred stock are "
        "affected, the written consent of the holders of a majority of the "
        "preferred stock then outstanding.",
    ),
)

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
        "Series A preferred: Kestrel Ventures LP holds 900,000 preferred "
        "shares issued 14 March 2024 at a price of USD 2.40 per share.",
        "Employee option grants outstanding: 410,000 options have been "
        "granted to employees under the company equity incentive plan.",
        "All shares are subject to the transfer restrictions set out in the "
        "Shareholders Agreement dated 14 March 2024.",
    ),
)

BOARD_MINUTES_2024_03 = DocSpec(
    filename="board_minutes_2024_03.pdf",
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

BOARD_MINUTES_2024_09 = DocSpec(
    filename="board_minutes_2024_09.pdf",
    doc_type="board_minutes",
    title="Northwind Analytics Inc. - Minutes of the Board of Directors, "
    "4 September 2024",
    paragraphs=(
        "Present: Sarah Chen (Chair), David Okonkwo, Rachel Imani.",
        "Resolution 1. The Board reviewed the proposed appointment of Priya "
        "Raghunathan as Chief Financial Officer and approved an annual base "
        "salary of USD 240,000 for that position.",
        "Resolution 2. The Board approved entry into a term loan facility "
        "with Meridian Bank in a principal amount not exceeding "
        "USD 3,000,000.",
        "Resolution 3. The Board discussed customer concentration and noted "
        "that a single customer represented a substantial share of revenue. "
        "Management was directed to pursue diversification.",
        "There being no further business, the meeting was closed.",
    ),
)

BOARD_MINUTES_2025_06 = DocSpec(
    filename="board_minutes_2025_06.pdf",
    doc_type="board_minutes",
    title="Northwind Analytics Inc. - Minutes of the Board of Directors, "
    "11 June 2025",
    paragraphs=(
        "Present: Sarah Chen (Chair), David Okonkwo, Rachel Imani, "
        "Priya Raghunathan in attendance.",
        "Resolution 1. The Board approved the appointment of Sterling Vance "
        "LLP as auditors for the financial year ending 31 December 2025.",
        "Resolution 2. The Board reviewed the reseller arrangement for the "
        "EMEA territory and approved its execution.",
        "Resolution 3. The Board received a report on outstanding employee "
        "option grants and requested a reconciliation at the next meeting.",
        "There being no further business, the meeting was closed.",
    ),
)

SHAREHOLDERS_AGREEMENT = DocSpec(
    filename="shareholders_agreement.pdf",
    doc_type="corporate_charter",
    title="Shareholders Agreement - Northwind Analytics Inc.",
    paragraphs=(
        "This Shareholders Agreement is dated 14 March 2024 and is made "
        "between Northwind Analytics Inc., Sarah Chen, David Okonkwo and "
        "Kestrel Ventures LP.",
        "Clause 4. Transfer restrictions. No holder may transfer shares "
        "without first offering them to the other holders on the same terms.",
        "Clause 7. Drag-along. If holders of more than sixty percent (60%) of "
        "the outstanding shares approve a sale of the company, all remaining "
        "holders are required to participate on the same terms.",
        "Clause 9. Preferred consent. For so long as Kestrel Ventures LP "
        "holds preferred shares, the written consent of Kestrel Ventures LP "
        "is required before the company may sell substantially all of its "
        "assets or effect a change of control.",
        "Clause 12. This Agreement is governed by the laws of the State of "
        "Delaware.",
    ),
)

SHARE_LEDGER = DocSpec(
    filename="stock_certificate_ledger.pdf",
    doc_type="cap_table",
    title="Stock Certificate Ledger - Northwind Analytics Inc.",
    paragraphs=(
        "Certificate CS-001 was issued to Sarah Chen on 19 June 2019 for "
        "1,800,000 shares of common stock.",
        "Certificate CS-002 was issued to David Okonkwo on 19 June 2019 for "
        "1,200,000 shares of common stock.",
        "Certificate PS-001 was issued to Kestrel Ventures LP on 14 March "
        "2024 for 900,000 shares of preferred stock.",
        "No further certificates have been issued as at the date of this "
        "ledger.",
    ),
)

CORPORATE_DOCUMENTS: tuple[DocSpec, ...] = (
    ARTICLES,
    BYLAWS,
    CAP_TABLE,
    BOARD_MINUTES_2024_03,
    BOARD_MINUTES_2024_09,
    BOARD_MINUTES_2025_06,
    SHAREHOLDERS_AGREEMENT,
    SHARE_LEDGER,
)
