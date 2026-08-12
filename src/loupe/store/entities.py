"""Entity name normalisation.

Extraction produces subject variants for the same entity: "TitanRetail Group
Limited" and "TitanRetail Group", "Northwind Analytics Inc." and "Northwind
Analytics". The tension detector groups claims by subject, so unmerged
variants mean contradictions between them are never compared -- the exact
failure this system exists to prevent.

This is deliberately not a full entity resolver. It is suffix stripping and
case folding: cheap, deterministic, no API cost, and it catches the variants
that actually occur. Coreference ("the Company", "the Supplier") is a harder
problem left to a later version.
"""

from __future__ import annotations

import re

CORPORATE_SUFFIXES = (
    "incorporated",
    "corporation",
    "limited",
    "company",
    "llc",
    "lllp",
    "llp",
    "plc",
    "gmbh",
    "pvt",
    "ltd",
    "inc",
    "corp",
    "co",
    "lp",
    "bv",
    "nv",
    "sa",
    "ag",
)

_PUNCT = re.compile(r"[.,]")
_WHITESPACE = re.compile(r"\s+")


def normalise_entity(name: str) -> str:
    """Reduce an entity name to a canonical key.

    Lowercases, strips punctuation and corporate suffixes, and collapses
    whitespace. Suffixes are stripped repeatedly so that "Acme Corp Ltd"
    reduces the same way as "Acme".

    Args:
        name: Raw subject string as extracted.

    Returns:
        A canonical key, or the cleaned original if stripping would empty it.

    Examples:
        >>> normalise_entity("TitanRetail Group Limited")
        'titanretail group'
        >>> normalise_entity("Northwind Analytics Inc.")
        'northwind analytics'
    """
    cleaned = _PUNCT.sub(" ", name.lower())
    cleaned = _WHITESPACE.sub(" ", cleaned).strip()
    if not cleaned:
        return name.strip().lower()

    words = cleaned.split(" ")
    while len(words) > 1 and words[-1] in CORPORATE_SUFFIXES:
        words.pop()

    result = " ".join(words).strip()
    return result or cleaned


def group_by_entity(subjects: list[str]) -> dict[str, list[str]]:
    """Map each canonical key to the raw variants that produced it.

    Useful for reporting how many variants were merged, and for debugging
    over-aggressive normalisation.
    """
    groups: dict[str, list[str]] = {}
    for subject in subjects:
        groups.setdefault(normalise_entity(subject), []).append(subject)
    return groups