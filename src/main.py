"""Stage 2: print the direct dependencies of a configured Maven package."""

import argparse
import sys

from config import load_config
from maven import Repository
from test_repository import direct_test_dependencies

ERROR_EXIT = 2


def show_dependencies(config, stream):
    """Print every direct declaration, including test and optional scopes."""
    if config.test_mode:
        dependencies = direct_test_dependencies(
            config.repository, config.package
        )
        lines = dependencies
    else:
        repository = Repository(config.repository)
        dependencies = repository.direct_dependencies(config.package,
                                                       config.version)
        lines = [dep.display() for dep in dependencies]
    print(f"Пакет: {config.package}, версия: {config.version}", file=stream)
    print("Прямые зависимости:", file=stream)
    for line in lines:
        print(line, file=stream)
    if not lines:
        print("(нет)", file=stream)


def main(argv=None):
    """Load the XML settings and report dependency or configuration errors."""
    parser = argparse.ArgumentParser(description="ПР 2, вариант 2: Maven")
    parser.add_argument("config", help="путь к XML с семью настройками")
    args = parser.parse_args(argv)
    try:
        show_dependencies(load_config(args.config), sys.stdout)
    except ValueError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return ERROR_EXIT
    return 0


if __name__ == "__main__":
    sys.exit(main())
