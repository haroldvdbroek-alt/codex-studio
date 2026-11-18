"""Start de voorbeeldapp met python -m project_package."""

from project_package.greeting import greet


def main() -> None:
    """Toon een begroeting met een fictieve naam."""
    print(greet("Voorbeeld"))


if __name__ == "__main__":
    main()
