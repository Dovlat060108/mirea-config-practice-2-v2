"""Read a small local letter-named graph for an offline demonstration."""

import json
from pathlib import Path
import re


def check_graph(graph):
    """Validate adjacency lists and require every referenced node to exist."""
    if not isinstance(graph, dict):
        raise ValueError("Тестовый репозиторий: нужен JSON-объект")
    for name, edges in graph.items():
        if not re.fullmatch(r"[A-Z]+", name):
            raise ValueError("Тестовый репозиторий: имена должны быть A-Z")
        if not isinstance(edges, list):
            raise ValueError(f"Узел {name}: требуется список зависимостей")
        for edge in edges:
            if not isinstance(edge, str) or edge not in graph:
                raise ValueError(f"Неизвестный узел тестового графа: {edge}")


def load_test_graph(filename):
    """Load and validate every adjacency list in the repository."""
    try:
        graph = json.loads(Path(filename).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        message = f"Не удалось прочитать тестовый граф: {error}"
        raise ValueError(message) from error
    check_graph(graph)
    return graph


def require_package(graph, package):
    """Report an absent starting package before traversing the graph."""
    if package not in graph:
        raise ValueError(f"В тестовом репозитории нет пакета {package}")


def direct_test_dependencies(filename, package):
    """Return the immediate neighbours of a package for stage 2."""
    graph = load_test_graph(filename)
    require_package(graph, package)
    return list(dict.fromkeys(graph[package]))
