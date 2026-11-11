"""Command line entry point for Maven dependency analysis."""

import argparse
import sys

from analysis import forward_graph, reverse_packages
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


def show_graph(config, stream):
    """Print the reachable graph and report edges that close a cycle."""
    graph = forward_graph(config)
    print(f"Граф зависимостей: {config.package}", file=stream)
    if not graph.edges:
        print("(пакет исключён фильтром)", file=stream)
    for node, targets in graph.edges.items():
        print(f"{node} -> {', '.join(targets) or 'нет зависимостей'}",
              file=stream)
    for start, end in graph.cycles:
        print(f"Цикл: {start} -> {end}", file=stream)


def show_reverse(config, stream, catalog):
    """Print all direct and indirect dependents of the selected package."""
    packages = reverse_packages(config, catalog)
    print(f"Обратные зависимости: {config.package}", file=stream)
    for package in packages:
        print(package, file=stream)
    if not packages:
        print("(нет)", file=stream)


def run_mode(args, config, stream):
    """Select an output mode for the loaded configuration."""
    if args.reverse:
        show_reverse(config, stream, args.catalog)
    elif args.direct:
        show_dependencies(config, stream)
    else:
        show_graph(config, stream)


def main(argv=None):
    """Load the XML settings and report dependency or configuration errors."""
    parser = argparse.ArgumentParser(description="ПР 2, вариант 2: Maven")
    parser.add_argument("config", help="путь к XML с семью настройками")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--direct", action="store_true",
                       help="показать прямые объявления POM (этап 2)")
    modes.add_argument("--reverse", action="store_true",
                       help="найти пакеты, зависящие от выбранного")
    parser.add_argument("--catalog", help="JSON-каталог для обратного Maven")
    args = parser.parse_args(argv)
    if args.catalog and not args.reverse:
        parser.error("--catalog используется вместе с --reverse")
    try:
        run_mode(args, load_config(args.config), sys.stdout)
    except RecursionError:
        print("Ошибка: граф слишком глубокий для рекурсивного DFS",
              file=sys.stderr)
        return ERROR_EXIT
    except ValueError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return ERROR_EXIT
    return 0


if __name__ == "__main__":
    sys.exit(main())
