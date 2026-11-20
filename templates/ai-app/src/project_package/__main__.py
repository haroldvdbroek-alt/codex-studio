"""Start een offline demonstratie met python -m project_package."""

from collections.abc import Mapping
import sys

from project_package.config import load_settings
from project_package.service import generate_reply


def main(environ: Mapping[str, str] | None = None) -> int:
    try:
        settings = load_settings(environ)
        reply = generate_reply("Geef een korte begroeting.", settings)
    except ValueError as error:
        print(f"Configuratiefout: {error}", file=sys.stderr)
        return 1
    print(reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
