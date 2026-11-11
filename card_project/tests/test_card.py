"""Классы эквивалентности и границы:
номер — корректный, неверная сумма, тип, символы и длины 15/16/17;
имя — два слова, число слов 0/1/2/3, длина слова 1/2, алфавит;
дата — два формата, месяцы 00/01/12/13, длина года 1/2/3/4/5;
CVV — цифры, тип, символы, длины 2/3/4.
В full_card_cases ровно одно ошибочное поле в каждом отрицательном кейсе.
Восемь pairwise-valid строк покрывают все пары двух выбранных валидных
значений четырех полей (D = A XOR B XOR C). Для состояний валидности
покрыты все разрешенные пары при ограничении PDF «не более одной ошибки».
"""

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
    """Читает пять массивов тестовых данных из JSON."""
    return {path.name: json.loads(path.read_text(encoding="utf-8"))
            for path in DATA_DIR.glob("*_cases.json")}


@pytest.fixture
def case(request, json_data):
    """Возвращает JSON-кейс для косвенной параметризации."""
    filename, index = request.param
    return json_data[filename][index]


class TestCard:
    """Класс с тестами для проверки данных карты."""

    @staticmethod
    @pytest.mark.parametrize("case", case_references("card_number_cases.json"), indirect=True)
    def test_is_valid_card_number(case):
        """Тестирование валидации номера карты."""
        # Arrange
        card_number = case["card_number"]
        expected = case["valid"]
        # Act
        actual_result = Card.is_valid_card_number(card_number)
        # Assert
        assert actual_result is expected, (
            f"Для card_number={card_number!r} ожидалось {expected}, получено {actual_result}"
        )

    @staticmethod
    @pytest.mark.parametrize("case", case_references("holder_name_cases.json"), indirect=True)
    def test_is_valid_card_holder_name(case):
        """Тестирование валидации имени владельца."""
        # Arrange
        holder_name, expected = case["holder_name"], case["valid"]
        # Act
        actual_result = Card.is_valid_card_holder_name(holder_name)
        # Assert
        assert actual_result is expected, f"holder_name={holder_name!r}"

    @staticmethod
    @pytest.mark.parametrize("case", case_references("expiry_date_cases.json"), indirect=True)
    def test_is_valid_expiry_date(case):
        """Тестирование валидации срока действия."""
        # Arrange
        expiry_date, expected = case["expiry_date"], case["valid"]
        # Act
        actual_result = Card.is_valid_expiry_date(expiry_date)
        # Assert
        assert actual_result is expected, f"expiry_date={expiry_date!r}"

    @staticmethod
    @pytest.mark.parametrize("case", case_references("cvv_cases.json"), indirect=True)
    def test_is_valid_cvv(case):
        """Тестирование валидации CVV."""
        # Arrange
        cvv, expected = case["cvv"], case["valid"]
        # Act
        actual_result = Card.is_valid_cvv(cvv)
        # Assert
        assert actual_result is expected, f"cvv case={case['id']}"

    @staticmethod
    @pytest.mark.parametrize("case", case_references("full_card_cases.json"), indirect=True)
    def test_is_valid_card(case):
        """Тестирование полной валидации карты."""
        # Arrange
        values = [case[key] for key in ("card_number", "holder_name", "expiry_date", "cvv")]
        expected = case["valid"]
        # Act
        actual_result = Card.is_valid_card(*values)
        # Assert
        assert actual_result is expected, f"full card case={case['id']}"

    @staticmethod
    @pytest.mark.parametrize("case", case_references("card_number_cases.json", "luhn_valid"), indirect=True)
    def test_luhn_check(case):
        """Тестирование алгоритма Луна, в том числе примеров из PDF."""
        # Arrange
        card_number, expected = case["card_number"], case["luhn_valid"]
        # Act
        actual_result = Card.luhn_check(card_number)
        # Assert
        assert actual_result is expected, f"luhn case={case['id']}"
