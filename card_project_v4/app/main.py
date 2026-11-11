from app.utils.card import Card


def main() -> None:

    valid = Card.is_valid_card("4539 1488 0343 6467", "JOHN SMITH", "12/2030", "123")
    print(f"Данные карты корректны: {valid}")


if __name__ == "__main__":
    main()
