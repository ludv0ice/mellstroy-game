from app.utils.card import Card


class TestCard:


    @staticmethod
    def test_is_valid_card_number(case):


        card_number = case["card_number"]
        expected = case["valid"]

        actual_result = Card.is_valid_card_number(card_number)

        assert actual_result is expected, (
            f"Для card_number={card_number!r} ожидалось {expected}, получено {actual_result}"
        )

    @staticmethod
    def test_is_valid_card_holder_name(case):


        holder_name, expected = case["holder_name"], case["valid"]

        actual_result = Card.is_valid_card_holder_name(holder_name)

        assert actual_result is expected, f"holder_name={holder_name!r}"

    @staticmethod
    def test_is_valid_expiry_date(case):


        expiry_date, expected = case["expiry_date"], case["valid"]

        actual_result = Card.is_valid_expiry_date(expiry_date)

        assert actual_result is expected, f"expiry_date={expiry_date!r}"

    @staticmethod
    def test_is_valid_cvv(case):


        cvv, expected = case["cvv"], case["valid"]

        actual_result = Card.is_valid_cvv(cvv)

        assert actual_result is expected, f"cvv case={case['id']}"

    @staticmethod
    def test_is_valid_card(case):


        values = [case[key] for key in ("card_number", "holder_name", "expiry_date", "cvv")]
        expected = case["valid"]

        actual_result = Card.is_valid_card(*values)

        assert actual_result is expected, f"full card case={case['id']}"

    @staticmethod
    def test_luhn_check(case):


        card_number, expected = case["card_number"], case["valid"]

        actual_result = Card.luhn_check(card_number)

        assert actual_result is expected, f"luhn case={case['id']}"
