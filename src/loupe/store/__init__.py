"""Shared evidence substrate."""

from loupe.store.entities import group_by_entity, normalise_entity
from loupe.store.evidence import EvidenceStore

__all__ = ["EvidenceStore", "group_by_entity", "normalise_entity"]