"""Claims: typed assertions extracted from documents.

A claim is one factual assertion a document makes, bound to the span that
supports it. Claims are the contents of the shared substrate -- the notice
board every agent writes to and the tension detector reads from.

Claims are deliberately atomic. "Acme has 4,250,000 shares issued" is one
claim. "Acme has 4,250,000 shares and 12 employees" is two. Atomicity is
what makes cross-document comparison mechanical rather than interpretive.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from loupe.models.span import Span


class ClaimType(StrEnum):
    """What kind of assertion this is.

    Type determines which comparisons are meaningful. Two MONETARY claims
    about the same subject can be compared arithmetically; two OBLIGATION
    claims cannot.
    """

    MONETARY = "monetary"
    QUANTITY = "quantity"
    DATE = "date"
    PARTY = "party"
    OBLIGATION = "obligation"
    RIGHT = "right"
    CONDITION = "condition"
    STATUS = "status"
    RELATIONSHIP = "relationship"


class Currency(StrEnum):
    """Currency tag for monetary claims.

    Mandatory on every monetary value. Comparing unlabelled numbers across
    documents is a real source of arithmetic error -- see edge cases.
    """

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    INR = "INR"
    UNKNOWN = "unknown"


class Claim(BaseModel):
    """A single typed assertion made by a document.

    Attributes:
        claim_id: Stable identifier.
        claim_type: Determines which comparisons apply.
        subject: Canonical entity the claim is about, once resolved.
        predicate: Short description of what is asserted.
        raw_text: The assertion as the document phrases it.
        span: Where it came from. Required -- there are no uncited claims.
        numeric_value: Parsed value for MONETARY and QUANTITY claims.
        currency: Required when numeric_value is monetary.
        date_value: Parsed value for DATE claims.
        extracted_by: Agent that produced it, for tracing.
        confidence: Extractor's self-reported confidence. Treated as a weak
            signal only -- models are poorly calibrated and default to near 1.0.
    """

    model_config = {"frozen": True}

    claim_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    claim_type: ClaimType
    subject: str = Field(min_length=1)
    predicate: str = Field(min_length=1)
    raw_text: str = Field(min_length=1)
    span: Span

    numeric_value: Decimal | None = None
    currency: Currency | None = None
    date_value: date | None = None

    extracted_by: str = "unknown"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _check_type_consistency(self) -> Claim:
        """Enforce that a claim carries the fields its type requires."""
        if self.claim_type is ClaimType.MONETARY:
            if self.numeric_value is None:
                raise ValueError("MONETARY claim requires numeric_value")
            if self.currency is None:
                raise ValueError(
                    "MONETARY claim requires currency -- unlabelled amounts "
                    "cannot be compared across documents"
                )
        if self.claim_type is ClaimType.QUANTITY and self.numeric_value is None:
            raise ValueError("QUANTITY claim requires numeric_value")
        if self.claim_type is ClaimType.DATE and self.date_value is None:
            raise ValueError("DATE claim requires date_value")
        if self.span.document_id != self.document_id:
            raise ValueError(
                f"span document_id {self.span.document_id!r} does not match "
                f"claim document_id {self.document_id!r}"
            )
        return self

    def is_comparable_to(self, other: Claim) -> bool:
        """True if comparing these two claims is meaningful.

        Requires same type, same subject, and -- for monetary claims --
        same currency. Guards against comparing USD to EUR.
        """
        if self.claim_type is not other.claim_type:
            return False
        if self.subject != other.subject:
            return False
        return not (
            self.claim_type is ClaimType.MONETARY
            and self.currency != other.currency
        )

    def is_cross_document(self, other: Claim) -> bool:
        """True if the two claims come from different documents."""
        return self.document_id != other.document_id