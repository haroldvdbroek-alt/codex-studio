"""Een kleine voorbeeldfunctie zonder externe afhankelijkheden."""


def greet(name: str) -> str:
    """Geef een begroeting terug; weiger een lege naam."""
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("De naam mag niet leeg zijn.")
    return f"Hallo, {cleaned_name}!"
