"""Command line entry point for Maven dependency analysis."""

import argparse
import sys

from analysis import forward_graph
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


def main(argv=None):
    """Load the XML settings and report dependency or configuration errors."""
    parser = argparse.ArgumentParser(description="ПР 2, вариант 2: Maven")
    parser.add_argument("config", help="путь к XML с семью настройками")
    parser.add_argument("--direct", action="store_true",
                        help="показать прямые объявления POM (этап 2)")
    args = parser.parse_args(argv)
    try:
        show = show_dependencies if args.direct else show_graph
        show(load_config(args.config), sys.stdout)
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
