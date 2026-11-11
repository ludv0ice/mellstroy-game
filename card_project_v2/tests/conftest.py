import json
from pathlib import Path

import pytest


DATA_DIR = Path(__file__).parent / "data"
CASE_FILES = {
    "test_is_valid_card_number": "card_number_cases.json",
    "test_is_valid_card_holder_name": "holder_name_cases.json",
    "test_is_valid_expiry_date": "expiry_date_cases.json",
    "test_is_valid_cvv": "cvv_cases.json",
    "test_is_valid_card": "full_card_cases.json",
    "test_luhn_check": "luhn_cases.json",
}


def read_cases(filename):

    return json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))


def pytest_generate_tests(metafunc):

    filename = CASE_FILES.get(metafunc.function.__name__)
    if filename is not None:
        rows = read_cases(filename)
        references = [(filename, index) for index in range(len(rows))]
        metafunc.parametrize("case", references, indirect=True, ids=[r["id"] for r in rows])


@pytest.fixture(scope="session")
def json_cases():

    return {path.name: read_cases(path.name) for path in sorted(DATA_DIR.glob("*_cases.json"))}


@pytest.fixture
def case(request, json_cases):

    filename, index = request.param
    return json_cases[filename][index]
