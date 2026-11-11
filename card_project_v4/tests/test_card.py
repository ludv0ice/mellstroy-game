import json
from pathlib import Path

import pytest

from app.utils.card import Card


DATA_DIR = Path(__file__).parent / "data"


def case_references(filename, expected_key="valid"):
    rows = json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))
    return [pytest.param((filename, i), id=row["id"])
            for i, row in enumerate(rows) if expected_key in row]


@pytest.fixture(scope="session")
def json_data():

    return {path.name: json.loads(path.read_text(encoding="utf-8"))
            for path in DATA_DIR.glob("*_cases.json")}


@pytest.fixture
def case(request, json_data):

    filename, index = request.param
    return json_data[filename][index]


class TestCard:


    @staticmethod
    @pytest.mark.parametrize("case", case_references("card_number_cases.json"), indirect=True)
    def test_is_valid_card_number(case):


        card_number = case["card_number"]
        expected = case["valid"]

        actual_result = Card.is_valid_card_number(card_number)

        assert actual_result is expected, (
            f"Для card_number={card_number!r} ожидалось {expected}, получено {actual_result}"
        )

    @staticmethod
    @pytest.mark.parametrize("case", case_references("holder_name_cases.json"), indirect=True)
    def test_is_valid_card_holder_name(case):


        holder_name, expected = case["holder_name"], case["valid"]

        actual_result = Card.is_valid_card_holder_name(holder_name)

        assert actual_result is expected, f"holder_name={holder_name!r}"

    @staticmethod
    @pytest.mark.parametrize("case", case_references("expiry_date_cases.json"), indirect=True)
    def test_is_valid_expiry_date(case):


        expiry_date, expected = case["expiry_date"], case["valid"]

        actual_result = Card.is_valid_expiry_date(expiry_date)

        assert actual_result is expected, f"expiry_date={expiry_date!r}"

    @staticmethod
    @pytest.mark.parametrize("case", case_references("cvv_cases.json"), indirect=True)
    def test_is_valid_cvv(case):


        cvv, expected = case["cvv"], case["valid"]

        actual_result = Card.is_valid_cvv(cvv)

        assert actual_result is expected, f"cvv case={case['id']}"

    @staticmethod
    @pytest.mark.parametrize("case", case_references("full_card_cases.json"), indirect=True)
    def test_is_valid_card(case):


        values = [case[key] for key in ("card_number", "holder_name", "expiry_date", "cvv")]
        expected = case["valid"]

        actual_result = Card.is_valid_card(*values)

        assert actual_result is expected, f"full card case={case['id']}"

    @staticmethod
    @pytest.mark.parametrize("case", case_references("card_number_cases.json", "luhn_valid"), indirect=True)
    def test_luhn_check(case):


        card_number, expected = case["card_number"], case["luhn_valid"]

        actual_result = Card.luhn_check(card_number)

        assert actual_result is expected, f"luhn case={case['id']}"
