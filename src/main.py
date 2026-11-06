"""Stage 1: configurable command line prototype."""

import argparse
import sys

from config import display_config, load_config

ERROR_EXIT = 2


def main(argv=None):
    """Load one XML file and print its validated settings."""
    parser = argparse.ArgumentParser(description="ПР 2, вариант 2: Maven")
    parser.add_argument("config", help="путь к XML с семью настройками")
    args = parser.parse_args(argv)
    try:
        display_config(load_config(args.config), sys.stdout)
    except ValueError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return ERROR_EXIT
    return 0


if __name__ == "__main__":
    sys.exit(main())
