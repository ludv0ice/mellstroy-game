"""Проверка данных карты: регулярные выражения и преобразование контрольной суммы."""

import re


class Card:
    """Класс для проверки корректности данных банковской карты."""

    @staticmethod
    def is_valid_card_number(card_number) -> bool:
        """Проверяет 16 цифр после удаления пробелов и алгоритм Луна."""
        if not isinstance(card_number, str):
            return False
        number = card_number.replace(" ", "")
        return len(number) == 16 and Card.luhn_check(number)

    @staticmethod
    def is_valid_card_holder_name(holder_name) -> bool:
        """Проверяет два латинских слова длиной больше одного символа."""
        return isinstance(holder_name, str) and bool(
            re.fullmatch(r"\s*[A-Za-z]{2,}\s+[A-Za-z]{2,}\s*", holder_name)
        )

    @staticmethod
    def is_valid_expiry_date(expiry_date) -> bool:
        """Проверяет формат MM/yy или MM/yyyy и допустимые месяц и год."""
        if not isinstance(expiry_date, str):
            return False
        if not re.fullmatch(r"(?:0[1-9]|1[0-2])/(?:[0-9]{2}|[0-9]{4})", expiry_date):
            return False
        year = expiry_date.partition("/")[2]
        return len(year) == 2 or year != "0000"

    @staticmethod
    def is_valid_cvv(cvv) -> bool:
        """Проверяет строку из трех цифр ASCII."""
        return isinstance(cvv, str) and len(cvv) == 3 and all("0" <= c <= "9" for c in cvv)

    @staticmethod
    def is_valid_card(card_number, holder_name, expiry_date, cvv) -> bool:
        """Проверяет все поля карты."""
        return (
            Card.is_valid_card_number(card_number)
            and Card.is_valid_card_holder_name(holder_name)
            and Card.is_valid_expiry_date(expiry_date)
            and Card.is_valid_cvv(cvv)
        )

    @staticmethod
    def luhn_check(card_number) -> bool:
        """Проверяет контрольную сумму, не ограничивая номер длиной 16."""
        if not isinstance(card_number, str):
            return False
        number = card_number.replace(" ", "")
        if not re.fullmatch(r"[0-9]{2,}", number):
            return False
        values = list(map(int, number[::-1]))
        doubled = [value * 2 for value in values[1::2]]
        checksum = sum(values[::2]) + sum(value // 10 + value % 10 for value in doubled)
        return checksum % 10 == 0
