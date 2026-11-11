"""Проверки заявленных свойств набора данных, независимо от валидаторов Card."""

from itertools import combinations, product

import pytest


FIELDS = ("card_number", "holder_name", "expiry_date", "cvv")
FILES = ("card_number_cases.json", "holder_name_cases.json", "expiry_date_cases.json", "cvv_cases.json")


def test_full_cases_have_at_most_one_invalid_field(json_cases):
    """Каждый отрицательный полный кейс меняет только одно поле эталона."""
    rows = json_cases["full_card_cases.json"]
    base = rows[0]
    for row in rows:
        if not row["valid"]:
            changed = [field for field in FIELDS if row[field] != base[field]]
            assert changed == [row["invalid_field"]], row["id"]
    for field, filename in zip(FIELDS, FILES):
        expected = [row[field] for row in json_cases[filename] if not row["valid"]]
        actual = [row[field] for row in rows if row.get("invalid_field") == field]
        assert actual == expected, field


@pytest.mark.parametrize("left,right", list(combinations(FIELDS, 2)))
def test_valid_pairwise_covers_every_value_pair(json_cases, left, right):
    """Все шесть пар полей содержат каждое сочетание двух выбранных уровней."""
    rows = [row for row in json_cases["full_card_cases.json"] if row.get("technique") == "pairwise-valid"]
    left_levels = {row[left] for row in rows}
    right_levels = {row[right] for row in rows}
    assert len(left_levels) == len(right_levels) == 2
    assert {(row[left], row[right]) for row in rows} == set(product(left_levels, right_levels))
