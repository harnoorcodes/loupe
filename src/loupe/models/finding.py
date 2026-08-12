"""Findings: the atomic unit of output.

A Finding is not a paragraph of prose -- it is a typed, addressable object
with evidence, severity, and a lifecycle. The memo is a rendering of the
confirmed findings, never a separate act of authorship.

That distinction is what makes the system evaluable: findings can be
compared against a known defect set to compute recall and precision.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from loupe.models.claim import Currency
from loupe.models.span import Span


class FindingType(StrEnum):
    """Defect classes. Mirrors the categories the eval harness plants."""

    ARITHMETIC = "arithmetic"
    CROSS_DOC_CONTRADICTION = "cross_doc_contradiction"
    TEMPORAL_IMPOSSIBILITY = "temporal_impossibility"
    LATENT_LIABILITY = "latent_liability"
    MISSING_DOCUMENT = "missing_document"
    UNDISCLOSED_RELATIONSHIP = "undisclosed_relationship"
    UNREADABLE_DOCUMENT = "unreadable_document"
    SUSPICIOUS_DOCUMENT = "suspicious_document"


class Severity(StrEnum):
    """How much this should worry the buyer."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingStatus(StrEnum):
    """Adversarial lifecycle.

    Findings are not trusted on creation. A finding must survive the red
    team critic to reach CONFIRMED. Nothing else enters the memo.

        PROPOSED -> CHALLENGED -> CONFIRMED
                              -> RETRACTED
    """

    PROPOSED = "proposed"
    CHALLENGED = "challenged"
    CONFIRMED = "confirmed"
    RETRACTED = "retracted"


_SEVERITY_ORDER = {
    Severity.LOW: 0,
    Severity.MEDIUM: 1,
    Severity.HIGH: 2,
    Severity.CRITICAL: 3,
}


class Finding(BaseModel):
    """A single identified risk, with evidence.

    Attributes:
        evidence: Spans supporting the finding. Required and non-empty for
            every type except MISSING_DOCUMENT, where the whole point is
            that no evidence exists.
        contradicts: Spans the evidence conflicts with, for contradiction
            types. This is what makes a cross-document finding legible.
        status: Lifecycle position. Only CONFIRMED reaches the memo.
        challenge_reason: What the critic argued, retained even on survival
            so a reviewer can see the objection that was overcome.
    """

    finding_id: str = Field(min_length=1)
    finding_type: FindingType
    severity: Severity
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)

    evidence: tuple[Span, ...] = ()
    contradicts: tuple[Span, ...] = ()
    claim_ids: tuple[str, ...] = ()

    materiality: Decimal | None = None
    materiality_currency: Currency | None = None

    status: FindingStatus = FindingStatus.PROPOSED
    challenge_reason: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    raised_by: str = "unknown"
    reviewed_by: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def _check_evidence(self) -> Finding:
        """Enforce provenance-or-abstain.

        Objective O-4. A finding without evidence is an assertion the
        reviewer cannot check, which is worse than no finding at all.
        MISSING_DOCUMENT is the sole exception -- absence is its content.
        """
        exempt = {FindingType.MISSING_DOCUMENT, FindingType.UNREADABLE_DOCUMENT}
        if self.finding_type not in exempt and not self.evidence:
            raise ValueError(
                f"{self.finding_type.value} finding requires at least one "
                f"evidence span"
            )
        if self.materiality is not None and self.materiality_currency is None:
            raise ValueError("materiality requires materiality_currency")
        return self

    @property
    def is_cross_document(self) -> bool:
        """True if evidence spans more than one document."""
        docs = {s.document_id for s in self.evidence + self.contradicts}
        return len(docs) > 1

    @property
    def severity_rank(self) -> int:
        """Sortable severity, highest first when negated."""
        return _SEVERITY_ORDER[self.severity]

    @property
    def all_spans(self) -> tuple[Span, ...]:
        """Every span this finding cites, for bulk validation."""
        return self.evidence + self.contradicts

    def challenge(self, reason: str, by: str) -> Finding:
        """Record a critic's objection. Returns a new Finding."""
        return self.model_copy(
            update={
                "status": FindingStatus.CHALLENGED,
                "challenge_reason": reason,
                "reviewed_by": (*self.reviewed_by, by),
            }
        )

    def confirm(self, by: str) -> Finding:
        """Admit a finding that survived challenge. Returns a new Finding.

        Raises:
            ValueError: If the finding was never challenged. Confirmation
                without adversarial review is not permitted -- it is the
                mechanism the whole design rests on.
        """
        if self.status is not FindingStatus.CHALLENGED:
            raise ValueError(
                f"cannot confirm a finding in state {self.status.value}; "
                f"it must be challenged first"
            )
        return self.model_copy(
            update={
                "status": FindingStatus.CONFIRMED,
                "reviewed_by": (*self.reviewed_by, by),
            }
        )

    def retract(self, reason: str, by: str) -> Finding:
        """Withdraw a finding. Returns a new Finding."""
        return self.model_copy(
            update={
                "status": FindingStatus.RETRACTED,
                "challenge_reason": reason,
                "reviewed_by": (*self.reviewed_by, by),
            }
        )