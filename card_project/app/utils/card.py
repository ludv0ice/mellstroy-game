"""Валидация полей карты по правилам учебного задания."""

import re


class Card:
    """Класс для проверки корректности данных банковской карты."""

    @staticmethod
    def is_valid_card_number(card_number) -> bool:
        """Проверяет строку из 16 цифр без пробелов и контрольную сумму Луна."""
        if not isinstance(card_number, str):
            return False
        number = card_number.replace(" ", "")
        return bool(re.fullmatch(r"[0-9]{16}", number)) and Card.luhn_check(number)

    @staticmethod
    def is_valid_card_holder_name(holder_name) -> bool:
        """Проверяет два слова из латинских букв, каждое длиной больше 1."""
        if not isinstance(holder_name, str):
            return False
        words = holder_name.split()
        return len(words) == 2 and all(
            re.fullmatch(r"[A-Za-z]{2,}", word) is not None for word in words
        )

    @staticmethod
    def is_valid_expiry_date(expiry_date) -> bool:
        """Проверяет MM/yy или MM/yyyy, месяц 01-12 и существующий год."""
        if not isinstance(expiry_date, str):
            return False
        match = re.fullmatch(r"(0[1-9]|1[0-2])/([0-9]{2}|[0-9]{4})", expiry_date)
        if match is None:
            return False
        year = match.group(2)
        return len(year) == 2 or int(year) >= 1

    @staticmethod
    def is_valid_cvv(cvv) -> bool:
        """Проверяет непустую строку ровно из трех цифр."""
        return isinstance(cvv, str) and re.fullmatch(r"[0-9]{3}", cvv) is not None

    @staticmethod
    def is_valid_card(card_number, holder_name, expiry_date, cvv) -> bool:
        """Возвращает True, только если все четыре поля валидны."""
        return (
            Card.is_valid_card_number(card_number)
            and Card.is_valid_card_holder_name(holder_name)
            and Card.is_valid_expiry_date(expiry_date)
            and Card.is_valid_cvv(cvv)
        )

    @staticmethod
    def luhn_check(card_number) -> bool:
        """Проверяет сумму Луна для строки минимум из двух цифр; удаляет пробелы."""
        if not isinstance(card_number, str):
            return False
        number = card_number.replace(" ", "")
        if re.fullmatch(r"[0-9]{2,}", number) is None:
            return False
        total = 0
        for position, char in enumerate(reversed(number)):
            digit = int(char)
            if position % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
        return total % 10 == 0
