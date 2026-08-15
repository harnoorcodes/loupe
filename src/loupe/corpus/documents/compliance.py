"""Compliance and intellectual property documents for Northwind Analytics.

Supports planted defects D-013 (intellectual property created before its
assignment took effect) and D-014 (a supplier sharing an address with a
founder).
"""

from __future__ import annotations

from loupe.corpus.spec import DocSpec

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
        "This assignment does not extend to work product created by third "
        "party contractors, which is addressed in the relevant contractor "
        "agreements.",
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
        "Technology errors and omissions coverage is provided with an "
        "aggregate limit of USD 3,000,000.",
    ),
)

TRADEMARK = DocSpec(
    filename="trademark_registration.pdf",
    doc_type="compliance_filing",
    title="Trademark Registration Certificate - NORTHWIND ANALYTICS",
    paragraphs=(
        "Registration number 6,214,889 was granted on 4 February 2022 for the "
        "word mark NORTHWIND ANALYTICS in international class 42.",
        "The registrant of record is Northwind Analytics Inc., a Delaware "
        "corporation.",
        "The registration is valid until 4 February 2032 subject to filing of "
        "the required declarations of continued use.",
        "No opposition proceedings were filed during the publication period.",
    ),
)

LITIGATION = DocSpec(
    filename="litigation_summary.pdf",
    doc_type="compliance_filing",
    title="Litigation and Claims Summary - as at 31 December 2025",
    paragraphs=(
        "The company is not party to any pending litigation as at the date of "
        "this summary.",
        "One commercial dispute was settled during 2025. A former reseller "
        "asserted unpaid commissions of USD 140,000; the matter settled for "
        "USD 62,000 without admission of liability.",
        "The company has received no regulatory enquiries during the period "
        "covered by this summary.",
        "Management is not aware of any circumstance likely to give rise to a "
        "claim exceeding USD 100,000.",
    ),
)

DPA = DocSpec(
    filename="data_processing_agreement.pdf",
    doc_type="compliance_filing",
    title="Data Processing Agreement - Northwind Analytics Inc.",
    paragraphs=(
        "This Data Processing Agreement is entered into on 19 August 2024 "
        "and forms part of the Master Subscription Agreement with Bluepeak "
        "Health Systems Inc.",
        "Northwind Analytics Inc. acts as processor in respect of personal "
        "data provided by the customer.",
        "Sub-processing is permitted only with prior written notice. The "
        "current approved sub-processor is CloudSpine Systems LLC for "
        "infrastructure hosting.",
        "Personal data is retained for the duration of the subscription and "
        "deleted within ninety (90) days of termination.",
    ),
)

VENDOR_LIST = DocSpec(
    filename="vendor_list.pdf",
    doc_type="other",
    title="Approved Vendor List - Northwind Analytics Inc.",
    paragraphs=(
        "CloudSpine Systems LLC, 44 Lakeshore Drive, Portland, Oregon. "
        "Infrastructure hosting. Annual spend approximately USD 570,000.",
        "Cedar Devshop LLC, 210 Cedar Street, Portland, Oregon. Contract "
        "software engineering. Annual spend approximately USD 216,000.",
        "Sterling Vance LLP, 1 Market Plaza, San Francisco, California. "
        "Audit and assurance. Annual spend approximately USD 85,000.",
        "Halden Recruitment Partners, 300 Pine Street, Seattle, Washington. "
        "Technical recruitment. Annual spend approximately USD 140,000.",
    ),
)

COMPLIANCE_DOCUMENTS: tuple[DocSpec, ...] = (
    IP_ASSIGNMENT,
    INSURANCE,
    TRADEMARK,
    LITIGATION,
    DPA,
    VENDOR_LIST,
)
