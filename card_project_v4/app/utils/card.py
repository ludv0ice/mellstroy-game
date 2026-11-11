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
        return len(words) == 2 and all(
            len(word) >= 2 and word.isascii() and word.isalpha() for word in words
        )

    @staticmethod
    def is_valid_expiry_date(expiry_date) -> bool:

        if not isinstance(expiry_date, str):
            return False
        month, separator, year = expiry_date.partition("/")
        if not separator or len(month) != 2 or len(year) not in (2, 4):
            return False
        combined = month + year
        if not combined.isascii() or not combined.isdecimal():
            return False
        return 1 <= int(month) <= 12 and (len(year) == 2 or int(year) != 0)

    @staticmethod
    def is_valid_cvv(cvv) -> bool:

        return isinstance(cvv, str) and len(cvv) == 3 and cvv.isascii() and cvv.isdecimal()

    @staticmethod
    def is_valid_card(card_number, holder_name, expiry_date, cvv) -> bool:

        return (
            Card.is_valid_card_number(card_number)
            and Card.is_valid_card_holder_name(holder_name)
            and Card.is_valid_expiry_date(expiry_date)
            and Card.is_valid_cvv(cvv)
        )

    @staticmethod
    def luhn_check(card_number) -> bool:

        if not isinstance(card_number, str):
            return False
        number = card_number.replace(" ", "")
        if len(number) < 2 or not number.isascii() or not number.isdecimal():
            return False
        total = 0
        parity = len(number) % 2
        for index, char in enumerate(number):
            value = int(char)
            if index % 2 == parity:
                value *= 2
                value = value - 9 * (value > 9)
            total += value
        return total % 10 == 0
