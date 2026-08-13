"""The diligence request list.

The buyer sends this to the seller at the start of a deal: a checklist of
every document expected in a complete data room. It is a real artifact of
the process, and it is what makes ABSENCE detectable.

A retrieval system can only report what it finds. By holding an explicit
expectation of what should exist, the system can report what does not --
which in real diligence is frequently the more valuable output. The missing
board consent, the unsigned amendment, the option plan that was never
adopted: none of these leave a trace in the data room.
"""

from __future__ import annotations

from typing import NamedTuple

from loupe.models.finding import Severity


class RequestItem(NamedTuple):
    """One expected document or category of documents.

    Attributes:
        item_id: Stable identifier.
        category: Diligence workstream this belongs to.
        title: What is being requested.
        keywords: Terms whose presence in a filename or document text
            indicates the request has been satisfied.
        severity: How serious its absence is.
        rationale: Why a buyer needs it, used in the finding description.
        conditional_on: Keywords that, if present anywhere in the corpus,
            make this item required. An empty tuple means always required.
    """

    item_id: str
    category: str
    title: str
    keywords: tuple[str, ...]
    severity: Severity
    rationale: str
    conditional_on: tuple[str, ...] = ()


REQUEST_LIST: tuple[RequestItem, ...] = (
    RequestItem(
        item_id="R-001",
        category="Corporate",
        title="Certificate or Articles of Incorporation",
        keywords=("articles of incorporation", "certificate of incorporation"),
        severity=Severity.CRITICAL,
        rationale=(
            "Establishes the legal existence of the entity being acquired. "
            "Without it the buyer cannot confirm what it is purchasing."
        ),
    ),
    RequestItem(
        item_id="R-002",
        category="Corporate",
        title="Capitalisation table",
        keywords=("capitalisation table", "capitalization table", "cap table"),
        severity=Severity.CRITICAL,
        rationale="Determines who owns what, and therefore who must consent.",
    ),
    RequestItem(
        item_id="R-003",
        category="Corporate",
        title="Board minutes and written consents",
        keywords=("minutes of the board", "board minutes", "written consent"),
        severity=Severity.HIGH,
        rationale="Evidences that corporate actions were properly authorised.",
    ),
    RequestItem(
        item_id="R-004",
        category="Corporate",
        title="Shareholders Agreement",
        keywords=("shareholders agreement", "stockholders agreement"),
        severity=Severity.HIGH,
        rationale=(
            "Governs transfer restrictions, drag-along and tag-along rights, "
            "any of which can block or complicate a sale."
        ),
    ),
    RequestItem(
        item_id="R-005",
        category="Equity",
        title="Equity incentive plan document",
        keywords=("equity incentive plan", "stock option plan", "option plan"),
        severity=Severity.HIGH,
        rationale=(
            "Options granted without an adopted plan may be invalid, leaving "
            "the company exposed to claims from holders and the cap table "
            "materially misstated."
        ),
        conditional_on=("option", "options granted", "equity incentive"),
    ),
    RequestItem(
        item_id="R-006",
        category="Financial",
        title="Audited or reviewed financial statements",
        keywords=("financial statements", "balance sheet", "income statement"),
        severity=Severity.CRITICAL,
        rationale="The basis of valuation and of the purchase price.",
    ),
    RequestItem(
        item_id="R-007",
        category="Financial",
        title="Accounts receivable ageing schedule",
        keywords=("receivable", "ageing", "aging schedule", "debtors"),
        severity=Severity.MEDIUM,
        rationale=(
            "Reveals collection risk that headline revenue figures conceal."
        ),
    ),
    RequestItem(
        item_id="R-008",
        category="Commercial",
        title="Material customer contracts",
        keywords=("subscription agreement", "master services", "customer contract","contract"),
        severity=Severity.CRITICAL,
        rationale=(
            "Contains the change-of-control, assignment and termination terms "
            "that determine whether revenue survives the transaction."
        ),
    ),
    RequestItem(
        item_id="R-009",
        category="Employment",
        title="Executive employment agreements",
        keywords=("employment agreement", "executive employment"),
        severity=Severity.HIGH,
        rationale="Establishes retention risk and severance exposure.",
    ),
    RequestItem(
        item_id="R-010",
        category="Intellectual Property",
        title="IP assignment agreements",
        keywords=("intellectual property assignment", "ip assignment", "invention"),
        severity=Severity.CRITICAL,
        rationale=(
            "Without these the company may not own the software it sells, "
            "which is usually the principal asset in a technology acquisition."
        ),
    ),
    RequestItem(
        item_id="R-011",
        category="Compliance",
        title="Insurance policies and certificates",
        keywords=("insurance", "certificate of insurance", "policy number"),
        severity=Severity.MEDIUM,
        rationale="Establishes coverage for pre-closing liabilities.",
    ),
    RequestItem(
        item_id="R-012",
        category="Compliance",
        title="Litigation schedule or no-litigation confirmation",
        keywords=("litigation", "proceedings", "no pending claims"),
        severity=Severity.HIGH,
        rationale=(
            "Undisclosed litigation is a common source of post-closing dispute."
        ),
    ),
    RequestItem(
        item_id="R-013",
        category="Financial",
        title="Debt agreements and loan documentation",
        keywords=("loan agreement", "promissory note", "credit facility"),
        severity=Severity.HIGH,
        rationale=(
            "Debt frequently carries change-of-control acceleration clauses."
        ),
    ),
    RequestItem(
        item_id="R-014",
        category="Tax",
        title="Tax returns for the last three years",
        keywords=("tax return", "form 1120", "corporation tax"),
        severity=Severity.HIGH,
        rationale="Unpaid or disputed tax transfers to the buyer.",
    ),
)