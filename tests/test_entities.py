"""Entity normalisation tests. All offline."""

from __future__ import annotations

import pytest

from loupe.store.entities import group_by_entity, normalise_entity


class TestNormalisation:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("TitanRetail Group Limited", "titanretail group"),
            ("TitanRetail Group", "titanretail group"),
            ("Northwind Analytics Inc.", "northwind analytics"),
            ("Northwind Analytics", "northwind analytics"),
            ("Meridian Logistics BV", "meridian logistics"),
            ("Kestrel Ventures LP", "kestrel ventures"),
            ("Acme Corp Ltd", "acme"),
            ("  Spaced   Out  Name  ", "spaced out name"),
        ],
    )
    def test_variants_collapse(self, raw: str, expected: str) -> None:
        assert normalise_entity(raw) == expected

    def test_the_titanretail_case(self) -> None:
        """The variant pair observed in the real extraction run."""
        assert normalise_entity("TitanRetail Group Limited") == normalise_entity(
            "TitanRetail Group"
        )

    def test_distinct_entities_stay_distinct(self) -> None:
        assert normalise_entity("Sarah Chen") != normalise_entity("David Okonkwo")

    def test_suffix_only_name_survives(self) -> None:
        """Stripping must not empty a name that is only a suffix word."""
        assert normalise_entity("Limited") == "limited"

    def test_empty_input(self) -> None:
        assert normalise_entity("") == ""

    def test_is_idempotent(self) -> None:
        once = normalise_entity("Northwind Analytics Inc.")
        assert normalise_entity(once) == once


class TestGrouping:
    def test_merges_variants(self) -> None:
        groups = group_by_entity(
            [
                "TitanRetail Group Limited",
                "TitanRetail Group",
                "Sarah Chen",
            ]
        )
        assert len(groups) == 2
        assert len(groups["titanretail group"]) == 2