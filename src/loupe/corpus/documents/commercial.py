"""Commercial documents for Northwind Analytics Inc.

Carries planted defects D-002 (change of control on the largest customer),
D-008 (an amendment supersedes a fee the accounts still use),
D-010 (a direct sale into an exclusive reseller territory) and
D-012 (an amendment dated before the amendment it amends).

The TitanRetail amendments exist specifically to expose the absence of
version handling. A system that treats every version as equally current
will report contradictions between a term and its own replacement.
"""

from __future__ import annotations

from loupe.corpus.spec import DocSpec

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

TITAN_AMENDMENT_1 = DocSpec(
    filename="contract_titanretail_amendment_1.pdf",
    doc_type="contract",
    title="Amendment No. 1 to Master Subscription Agreement - TitanRetail Group",
    paragraphs=(
        "This Amendment No. 1 is dated 12 January 2025 and amends the Master "
        "Subscription Agreement between Northwind Analytics Inc. and "
        "TitanRetail Group Limited dated 8 May 2024.",
        "Section 1. Section 4 of the Agreement is deleted in its entirety and "
        "replaced with the following: Customer shall pay an annual "
        "subscription fee of USD 4,100,000 payable quarterly in advance, "
        "effective from 1 February 2025.",
        "Section 2. Section 3 of the Agreement is amended to extend the "
        "initial term to forty-eight (48) months from the original Effective "
        "Date.",
        "Section 3. All other terms of the Agreement remain in full force and "
        "effect, including without limitation Section 11.",
    ),
)

TITAN_AMENDMENT_2 = DocSpec(
    filename="contract_titanretail_amendment_2.pdf",
    doc_type="contract",
    title="Amendment No. 2 to Master Subscription Agreement - TitanRetail Group",
    paragraphs=(
        "This Amendment No. 2 is dated 3 November 2024 and further amends the "
        "Master Subscription Agreement between Northwind Analytics Inc. and "
        "TitanRetail Group Limited as previously amended by Amendment No. 1.",
        "Section 1. The service level commitment in Schedule B is amended to "
        "provide for 99.9% monthly availability.",
        "Section 2. Customer's right to terminate under Section 11 of the "
        "Agreement is unaffected by this Amendment.",
        "Section 3. All other terms of the Agreement as amended remain in "
        "full force and effect.",
    ),
)

MERIDIAN_CONTRACT = DocSpec(
    filename="contract_meridian.pdf",
    doc_type="contract",
    title="Master Subscription Agreement - Meridian Logistics",
    paragraphs=(
        "This Master Subscription Agreement is entered into on 2 February "
        "2025 between Northwind Analytics Inc. and Meridian Logistics BV.",
        "Section 3. Term. The initial term is twenty-four (24) months "
        "commencing on the Effective Date.",
        "Section 4. Fees. Customer shall pay an annual subscription fee of "
        "USD 1,008,000 payable annually in advance.",
        "Section 11. Assignment. This Agreement may be assigned by either "
        "party to a successor in interest without consent.",
    ),
)

BLUEPEAK_CONTRACT = DocSpec(
    filename="contract_bluepeak.pdf",
    doc_type="contract",
    title="Master Subscription Agreement - Bluepeak Health",
    paragraphs=(
        "This Master Subscription Agreement is entered into on 19 August 2024 "
        "between Northwind Analytics Inc. and Bluepeak Health Systems Inc.",
        "Section 3. Term. The initial term is twelve (12) months commencing "
        "on the Effective Date and renews automatically unless terminated.",
        "Section 4. Fees. Customer shall pay an annual subscription fee of "
        "USD 756,000 payable annually in advance.",
        "Section 8. Data protection. Supplier shall process personal health "
        "information only in accordance with the Data Processing Agreement "
        "executed alongside this Agreement.",
        "Section 11. Termination for convenience. Either party may terminate "
        "on ninety (90) days written notice.",
    ),
)

NOVACLEAR_CONTRACT = DocSpec(
    filename="contract_novaclear.pdf",
    doc_type="contract",
    title="Master Subscription Agreement - NovaClear GmbH",
    paragraphs=(
        "This Master Subscription Agreement is entered into on 15 June 2025 "
        "between Northwind Analytics Inc. and NovaClear GmbH, whose "
        "registered office is at Maximilianstrasse 14, 80539 Munich, "
        "Germany.",
        "Section 3. Term. The initial term is twenty-four (24) months "
        "commencing on the Effective Date.",
        "Section 4. Fees. Customer shall pay an annual subscription fee of "
        "USD 1,344,000 payable annually in advance.",
        "Section 6. Territory. Services are provided for Customer's "
        "operations across Germany, Austria and Switzerland.",
        "Section 11. Assignment. Neither party may assign this Agreement "
        "without prior written consent.",
    ),
)

PACIFICA_RESELLER = DocSpec(
    filename="reseller_agreement_pacifica.pdf",
    doc_type="contract",
    title="Exclusive Reseller Agreement - Pacifica Systems Pte Ltd",
    paragraphs=(
        "This Reseller Agreement is entered into on 1 March 2025 between "
        "Northwind Analytics Inc. and Pacifica Systems Pte Ltd.",
        "Section 2. Appointment. Supplier appoints Reseller as its exclusive "
        "reseller for the EMEA territory, comprising Europe, the Middle East "
        "and Africa, for the term of this Agreement.",
        "Section 3. Exclusivity. During the term, Supplier shall not sell, "
        "license or provide the Services directly to any customer whose "
        "principal place of business is within the EMEA territory, nor "
        "appoint any other reseller for that territory.",
        "Section 5. Term. The initial term is thirty-six (36) months "
        "commencing 1 March 2025.",
        "Section 9. Remedies. Breach of Section 3 entitles Reseller to "
        "liquidated damages equal to twelve (12) months of the affected "
        "revenue, and to terminate this Agreement immediately.",
    ),
)

CLOUDSPINE_SUPPLIER = DocSpec(
    filename="supplier_cloudspine.pdf",
    doc_type="contract",
    title="Infrastructure Services Agreement - CloudSpine Systems LLC",
    paragraphs=(
        "This Infrastructure Services Agreement is entered into on 5 January "
        "2024 between Northwind Analytics Inc. and CloudSpine Systems LLC, a "
        "limited liability company whose registered address is 44 Lakeshore "
        "Drive, Portland, Oregon.",
        "Section 2. Services. Supplier provides managed hosting, storage and "
        "network capacity for the Customer's production environment.",
        "Section 4. Fees. Customer shall pay a monthly fee of USD 47,500, "
        "subject to annual review.",
        "Section 7. Term. The initial term is thirty-six (36) months and "
        "renews automatically for successive twelve month periods.",
        "Section 10. Termination. Either party may terminate for convenience "
        "on one hundred and eighty (180) days written notice.",
    ),
)

COMMERCIAL_DOCUMENTS: tuple[DocSpec, ...] = (
    TITAN_CONTRACT,
    TITAN_AMENDMENT_1,
    TITAN_AMENDMENT_2,
    MERIDIAN_CONTRACT,
    BLUEPEAK_CONTRACT,
    NOVACLEAR_CONTRACT,
    PACIFICA_RESELLER,
    CLOUDSPINE_SUPPLIER,
)
