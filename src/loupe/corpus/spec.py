"""Shared types for the synthetic corpus and its ground truth."""

from __future__ import annotations

from typing import NamedTuple


class DocSpec(NamedTuple):
    """A document to generate.

    Attributes:
        filename: Output name. The extension decides PDF or DOCX.
        doc_type: Expected classification, used to check the classifier.
        title: Heading rendered at the top of the document.
        paragraphs: Body text, one entry per paragraph.
    """

    filename: str
    doc_type: str
    title: str
    paragraphs: tuple[str, ...]


class PlantedDefect(NamedTuple):
    """A defect deliberately introduced into the corpus.

    Attributes:
        defect_id: Stable identifier.
        name: Short human label for the results table.
        accepted_types: Finding types that count as a correct detection.
            More than one is allowed because a single real problem can be
            correctly classified in several ways -- a change-of-control
            exposure is both a cross-document contradiction and a latent
            liability, and insisting on one label would score a correct
            answer as a miss.
        documents: Files that must be read together to detect it.
        anchors: Short text fragments a correct finding should mention.
            Only ONE needs to appear. Kept short deliberately, because a
            finding may quote a narrower span than the sentence the defect
            lives in.
        difficulty: easy | medium | hard. Hard defects are expected to fail
            until the corresponding capability is built, and are included
            precisely for that reason -- a benchmark that scores 100% on
            first run is measuring the benchmark, not the system.
        requires: Capability needed to detect it, for the results table.
        description: What a correct finding would say.
    """

    defect_id: str
    name: str
    accepted_types: tuple[str, ...]
    documents: tuple[str, ...]
    anchors: tuple[str, ...]
    difficulty: str
    requires: str
    description: str


class ExpectedGap(NamedTuple):
    """A document genuinely absent from this corpus but never planted.

    Reporting these is CORRECT behaviour, not a false positive, so the score
    card counts them separately rather than penalising the system for being
    right about something it was not asked about.
    """

    request_id: str
    reason: str
