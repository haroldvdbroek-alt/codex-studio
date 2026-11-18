"""Commandoregel met dry-run als standaard en logging naar stderr."""

import argparse
import logging

from project_package.tasks import process_files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verwerk UTF-8 .txt-bestanden zonder bronwijzigingen.")
    parser.add_argument("source", help="Bestaande bronmap")
    parser.add_argument("destination", help="Nieuwe, niet-bestaande doelmap")
    parser.add_argument("--apply", action="store_true", help="Schrijf echt; standaard alleen dry-run")
    args = parser.parse_args(argv)
    # Een eigen logger: geen globale loggingconfiguratie of logbestand.
    logger = logging.Logger("project_package.automation", level=logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(handler)
    try:
        process_files(args.source, args.destination, apply=args.apply, logger=logger)
    except ValueError as error:
        logger.error("%s", error)
        return 1
    except OSError as error:
        logger.error("Bestandsbewerking mislukt (%s). Controleer paden en rechten; "
                     "een gedeeltelijk nieuw doel kan achterblijven.", type(error).__name__)
        return 1
    finally:
        handler.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
