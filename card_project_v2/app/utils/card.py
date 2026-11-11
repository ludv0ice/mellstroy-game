from string import ascii_letters, digits


class Card:


    @staticmethod
    def is_valid_card_number(card_number) -> bool:
        if not isinstance(card_number, str):
            return False
        number = card_number.replace(" ", "")
        return len(number) == 16 and Card.luhn_check(number)

    @staticmethod
    def is_valid_card_holder_name(holder_name) -> bool:
        if not isinstance(holder_name, str):
            return False
        words = holder_name.split()
        if len(words) != 2:
            return False
        return all(len(word) > 1 and all(c in ascii_letters for c in word) for word in words)

    @staticmethod
    def is_valid_expiry_date(expiry_date) -> bool:
        if not isinstance(expiry_date, str):
            return False
        parts = expiry_date.split("/")
        if len(parts) != 2:
            return False
        month, year = parts
        if len(month) != 2 or len(year) not in (2, 4):
            return False
        if not all(c in digits for c in month + year):
            return False
        return 1 <= int(month) <= 12 and (len(year) == 2 or int(year) > 0)

    @staticmethod
    def is_valid_cvv(cvv) -> bool:
        return isinstance(cvv, str) and len(cvv) == 3 and all(c in digits for c in cvv)

    @staticmethod
    def is_valid_card(card_number, holder_name, expiry_date, cvv) -> bool:
        checks = (
            Card.is_valid_card_number(card_number),
            Card.is_valid_card_holder_name(holder_name),
            Card.is_valid_expiry_date(expiry_date),
            Card.is_valid_cvv(cvv),
        )
        return all(checks)

    @staticmethod
    def luhn_check(card_number) -> bool:
        if not isinstance(card_number, str):
            return False
        number = card_number.replace(" ", "")
        if len(number) < 2 or not all(c in digits for c in number):
            return False
        doubled = (0, 2, 4, 6, 8, 1, 3, 5, 7, 9)
        values = [int(c) for c in reversed(number)]
        checksum = sum(values[::2]) + sum(doubled[value] for value in values[1::2])
        return checksum % 10 == 0
