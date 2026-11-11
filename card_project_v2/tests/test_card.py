"""Тесты по шаблону PDF: TestCard, статические методы и Arrange/Act/Assert."""

from app.utils.card import Card


class TestCard:
    """Класс с тестами для проверки данных карты."""

    @staticmethod
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
    def test_is_valid_card_holder_name(case):
        """Тестирование валидации имени владельца."""
        # Arrange
        holder_name, expected = case["holder_name"], case["valid"]
        # Act
        actual_result = Card.is_valid_card_holder_name(holder_name)
        # Assert
        assert actual_result is expected, f"holder_name={holder_name!r}"

    @staticmethod
    def test_is_valid_expiry_date(case):
        """Тестирование валидации срока действия."""
        # Arrange
        expiry_date, expected = case["expiry_date"], case["valid"]
        # Act
        actual_result = Card.is_valid_expiry_date(expiry_date)
        # Assert
        assert actual_result is expected, f"expiry_date={expiry_date!r}"

    @staticmethod
    def test_is_valid_cvv(case):
        """Тестирование валидации CVV."""
        # Arrange
        cvv, expected = case["cvv"], case["valid"]
        # Act
        actual_result = Card.is_valid_cvv(cvv)
        # Assert
        assert actual_result is expected, f"cvv case={case['id']}"

    @staticmethod
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
    def test_luhn_check(case):
        """Тестирование алгоритма Луна, в том числе примеров из PDF."""
        # Arrange
        card_number, expected = case["card_number"], case["valid"]
        # Act
        actual_result = Card.luhn_check(card_number)
        # Assert
        assert actual_result is expected, f"luhn case={case['id']}"
