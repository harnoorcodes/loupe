"""Ground truth: every defect deliberately planted in the corpus.

Fifteen defects across six classes. Difficulty is recorded per defect
because a benchmark that scores 100% on first run is measuring the
benchmark, not the system.

Four defects are marked HARD and are expected to fail against the current
implementation:

  D-008  needs version handling: an amendment supersedes a fee
  D-010  needs a three-document chain and geographic inference
  D-013  needs inference from a delivery date to an assignment date
  D-015  needs coreference across a surname and a shared address

Those four exist to expose real gaps, and are the targets for the
version-handling and coreference milestones. Reporting an honest 11 of 15
with a per-class breakdown is more informative than a clean sweep of
defects chosen to be findable.
"""

from __future__ import annotations

from loupe.corpus.spec import ExpectedGap, PlantedDefect

PLANTED_DEFECTS: tuple[PlantedDefect, ...] = (
    # ---------------------------------------------------------- arithmetic
    PlantedDefect(
        defect_id="D-001",
        name="Share total does not reconcile",
        accepted_types=("arithmetic",),
        documents=("cap_table.pdf",),
        anchors=("4,250,000",),
        difficulty="easy",
        requires="arithmetic reconciliation",
        description=(
            "The cap table states 4,250,000 shares issued and outstanding. "
            "Identified holdings are 1,800,000 + 1,200,000 + 900,000 = "
            "3,900,000. 350,000 shares have no identified holder. "
            "Unexercised options are correctly excluded, being not yet "
            "issued."
        ),
    ),
    PlantedDefect(
        defect_id="D-004",
        name="Option grants exceed the cap table figure",
        accepted_types=("arithmetic", "cross_doc_contradiction"),
        documents=("option_grant_schedule.docx", "cap_table.pdf"),
        anchors=("410,000", "120,000"),
        difficulty="medium",
        requires="cross-document arithmetic",
        description=(
            "The option grant schedule lists individual grants of 120,000 + "
            "95,000 + 80,000 + 75,000 + 45,000 + 30,000 = 445,000 options. "
            "The cap table states 410,000 options outstanding. The 35,000 "
            "difference means either the cap table understates dilution or "
            "grants were made outside the recorded plan."
        ),
    ),
    PlantedDefect(
        defect_id="D-005",
        name="Revenue schedule exceeds stated total revenue",
        accepted_types=("arithmetic", "cross_doc_contradiction"),
        documents=("revenue_by_customer_2025.pdf", "financial_statements_2025.pdf"),
        anchors=("8,400,000", "1,344,000"),
        difficulty="medium",
        requires="cross-document arithmetic",
        description=(
            "The revenue by customer schedule lists 3,612,000 + 1,344,000 + "
            "1,008,000 + 890,000 + 756,000 + 1,000,000 = 8,610,000. The "
            "financial statements report total revenue of 8,400,000. The "
            "210,000 difference is unexplained."
        ),
    ),
    # ------------------------------------------- cross-document contradiction
    PlantedDefect(
        defect_id="D-006",
        name="CFO salary contradicts the board resolution",
        accepted_types=("cross_doc_contradiction",),
        documents=("employment_cfo.docx", "board_minutes_2024_09.pdf"),
        anchors=("260,000", "240,000"),
        difficulty="medium",
        requires="cross-document comparison",
        description=(
            "The CFO employment agreement provides for an annual base salary "
            "of USD 260,000. The board minutes of 4 September 2024 approved "
            "USD 240,000 for that position. The executed agreement exceeds "
            "the approved amount by USD 20,000 per annum, which may mean the "
            "compensation was never properly authorised."
        ),
    ),
    PlantedDefect(
        defect_id="D-007",
        name="Deferred revenue stated differently in two documents",
        accepted_types=("cross_doc_contradiction", "arithmetic"),
        documents=("deferred_revenue_schedule.pdf", "financial_statements_2025.pdf"),
        anchors=("2,340,000", "2,100,000"),
        difficulty="medium",
        requires="cross-document comparison",
        description=(
            "The financial statements report deferred revenue of "
            "USD 2,100,000 at 31 December 2025. The deferred revenue "
            "schedule for the same date totals USD 2,340,000. The 240,000 "
            "difference affects both the balance sheet and the revenue "
            "recognised in the period."
        ),
    ),
    PlantedDefect(
        defect_id="D-008",
        name="Revenue recognised on a superseded fee",
        accepted_types=("cross_doc_contradiction", "arithmetic"),
        documents=(
            "contract_titanretail_amendment_1.pdf",
            "revenue_by_customer_2025.pdf",
        ),
        anchors=("4,100,000", "3,612,000"),
        difficulty="hard",
        requires="version handling: knowing an amendment supersedes a term",
        description=(
            "Amendment No. 1 dated 12 January 2025 replaced the TitanRetail "
            "annual fee with USD 4,100,000 effective 1 February 2025. The "
            "FY2025 revenue schedule still records USD 3,612,000 for that "
            "customer, the pre-amendment figure. Either revenue is "
            "understated by approximately USD 447,000 for the eleven months "
            "the amended fee applied, or the amendment was never invoiced."
        ),
    ),
    # ----------------------------------------------------- latent liability
    PlantedDefect(
        defect_id="D-002",
        name="Change of control right held by the largest customer",
        accepted_types=("latent_liability", "cross_doc_contradiction"),
        documents=("contract_titanretail.pdf", "financial_statements_2025.pdf"),
        anchors=("43%", "thirty (30) days"),
        difficulty="easy",
        requires="cross-document reasoning",
        description=(
            "TitanRetail may terminate on a change of control without "
            "penalty, and represents 43% of FY2025 revenue. An acquisition "
            "puts USD 3,612,000 of annual revenue at immediate risk."
        ),
    ),
    PlantedDefect(
        defect_id="D-009",
        name="Loan acceleration exceeds available cash",
        accepted_types=("latent_liability", "cross_doc_contradiction"),
        documents=("loan_agreement_meridian_bank.pdf", "financial_statements_2025.pdf"),
        anchors=("3,000,000", "1,940,000"),
        difficulty="medium",
        requires="cross-document reasoning",
        description=(
            "The Meridian Bank facility accelerates in full on a change of "
            "control, at the lender's election. Outstanding principal is "
            "USD 3,000,000 while cash at year end was USD 1,940,000. An "
            "acquisition could trigger a repayment obligation the company "
            "cannot meet from cash on hand."
        ),
    ),
    PlantedDefect(
        defect_id="D-010",
        name="Direct sale into an exclusive reseller territory",
        accepted_types=("latent_liability", "cross_doc_contradiction"),
        documents=(
            "reseller_agreement_pacifica.pdf",
            "contract_novaclear.pdf",
        ),
        anchors=("exclusive reseller", "Munich", "liquidated damages"),
        difficulty="hard",
        requires="three-document chain plus geographic inference",
        description=(
            "Pacifica holds exclusive EMEA reseller rights from 1 March 2025, "
            "and Section 3 prohibits direct sales into that territory. The "
            "NovaClear agreement dated 15 June 2025 is a direct contract with "
            "a customer registered in Munich, Germany, which is within EMEA. "
            "Breach entitles Pacifica to liquidated damages of twelve months "
            "of affected revenue and to terminate."
        ),
    ),
    # ------------------------------------------------------ missing document
    PlantedDefect(
        defect_id="D-003",
        name="Equity incentive plan referenced but absent",
        accepted_types=("missing_document",),
        documents=(),
        anchors=("equity incentive plan",),
        difficulty="easy",
        requires="negative space audit",
        description=(
            "410,000 options are stated as granted under an equity incentive "
            "plan, and the board minutes record only an intention to prepare "
            "one. No plan document is present in the data room."
        ),
    ),
    PlantedDefect(
        defect_id="D-011",
        name="Board consent for CFO appointment absent",
        accepted_types=("missing_document",),
        documents=(),
        anchors=("written consent", "9 September 2024"),
        difficulty="medium",
        requires="negative space audit driven by a document reference",
        description=(
            "The CFO employment agreement records that the appointment was "
            "approved by written consent of the Board dated 9 September 2024. "
            "No such consent appears in the data room, and the bylaws require "
            "board approval for any officer appointment."
        ),
    ),
    # ----------------------------------------------- temporal impossibility
    PlantedDefect(
        defect_id="D-012",
        name="Amendment dated before the amendment it amends",
        accepted_types=("temporal_impossibility", "cross_doc_contradiction"),
        documents=(
            "contract_titanretail_amendment_2.pdf",
            "contract_titanretail_amendment_1.pdf",
        ),
        anchors=("3 November 2024", "12 January 2025"),
        difficulty="medium",
        requires="date ordering across documents",
        description=(
            "Amendment No. 2 is dated 3 November 2024 and states that it "
            "further amends the agreement as previously amended by Amendment "
            "No. 1. Amendment No. 1 is dated 12 January 2025. An amendment "
            "cannot modify a document that did not yet exist."
        ),
    ),
    PlantedDefect(
        defect_id="D-013",
        name="Contractor IP created before its assignment took effect",
        accepted_types=("temporal_impossibility", "latent_liability"),
        documents=(
            "contractor_agreement_devshop.docx",
            "management_accounts_q1_2026.pdf",
        ),
        anchors=("November 2024", "1 March 2025", "analytics engine"),
        difficulty="hard",
        requires="inference from a delivery date to an assignment date",
        description=(
            "The Cedar Devshop contractor agreement assigns work product to "
            "the company effective from 1 March 2025. The management accounts "
            "record that the analytics engine rewrite was delivered by "
            "external contractors in November 2024. The IP assignment does "
            "not cover work created before it took effect, so the company may "
            "not own a core component of its product."
        ),
    ),
    # -------------------------------------------- undisclosed relationship
    PlantedDefect(
        defect_id="D-014",
        name="Supplier shares an address with the CEO",
        accepted_types=("undisclosed_relationship", "cross_doc_contradiction"),
        documents=("supplier_cloudspine.pdf", "employment_ceo.docx"),
        anchors=("44 Lakeshore Drive",),
        difficulty="medium",
        requires="matching an address across documents",
        description=(
            "CloudSpine Systems LLC is registered at 44 Lakeshore Drive, "
            "Portland, Oregon, which is also the residential address of the "
            "Chief Executive Officer. Annual spend with this supplier is "
            "approximately USD 570,000. The relationship is not disclosed as "
            "a related party transaction anywhere in the data room."
        ),
    ),
    PlantedDefect(
        defect_id="D-015",
        name="Contractor connected to the CTO",
        accepted_types=("undisclosed_relationship", "cross_doc_contradiction"),
        documents=("contractor_agreement_devshop.docx", "employment_cto.docx"),
        anchors=("210 Cedar Street", "S. Okonkwo"),
        difficulty="hard",
        requires="coreference across an abbreviated name and a shared address",
        description=(
            "Cedar Devshop LLC has a principal recorded as S. Okonkwo and a "
            "registered address of 210 Cedar Street, Portland, Oregon, which "
            "is the residential address of the Chief Technology Officer, "
            "David Okonkwo. Annual spend is approximately USD 216,000 and the "
            "relationship is not disclosed."
        ),
    ),
)


EXPECTED_GAPS: tuple[ExpectedGap, ...] = (
    ExpectedGap(
        "R-014", "No tax returns were written for this corpus."
    ),
)


# --------------------------------------------------------------- reporting

DIFFICULTY_ORDER = ("easy", "medium", "hard")

DEFECT_CLASSES = (
    "arithmetic",
    "cross_doc_contradiction",
    "latent_liability",
    "missing_document",
    "temporal_impossibility",
    "undisclosed_relationship",
)


def primary_class(defect: PlantedDefect) -> str:
    """The class a defect is filed under in the results table.

    A defect may accept several finding types, but is counted once, under
    the first accepted type, so per-class totals sum to the overall total.
    """
    return defect.accepted_types[0]
