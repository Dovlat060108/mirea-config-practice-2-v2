"""Connect graph traversal to the local or Maven repository."""

import json
from pathlib import Path
import re

from config import VERSION_PATTERN, check_package
from graph import build_graph, reverse_dependents
from maven import Repository
from test_repository import load_test_graph, require_package

MAVEN_SCOPES = {"compile", "runtime"}


def maven_neighbours(repository, coordinate):
    """Read the required compile and runtime dependencies of a Maven node."""
    package, version = coordinate.rsplit(":", 1)
    deps = repository.direct_dependencies(package, version)
    return [
        f"{dep.group}:{dep.artifact}:{dep.version}" for dep in deps
        if dep.scope in MAVEN_SCOPES and dep.optional != "true"
    ]


def forward_graph(config):
    """Build a graph reachable from the configured package and version."""
    if config.test_mode:
        source = load_test_graph(config.repository)
        require_package(source, config.package)
        return build_graph(
            [config.package], source.__getitem__,
            lambda name: matches(name, config.filter),
        )
    repository = Repository(config.repository)
    return build_graph(
        [f"{config.package}:{config.version}"],
        lambda node: maven_neighbours(repository, node),
        lambda node: matches(node.rsplit(":", 1)[0], config.filter),
    )


def matches(name, fragment):
    """Match a nonempty filter against the package name, case sensitively."""
    return bool(fragment) and fragment in name


def load_catalog(filename):
    """Read a finite set of Maven coordinates for a reverse search."""
    try:
        roots = json.loads(Path(filename).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        message = f"Не удалось прочитать каталог Maven: {error}"
        raise ValueError(message) from error
    if not isinstance(roots, list) or not roots:
        raise ValueError("Каталог Maven: нужен непустой JSON-массив координат")
    for coordinate in roots:
        if not isinstance(coordinate, str) or ":" not in coordinate:
            raise ValueError("Каталог Maven: нужно groupId:artifactId:version")
        package, version = coordinate.rsplit(":", 1)
        check_package(package, False)
        if not re.fullmatch(VERSION_PATTERN, version):
            raise ValueError(f"Каталог Maven: неверная версия в {coordinate}")
    return roots


def reverse_packages(config, catalog=None):
    """Use the stage 3 DFS to search the whole local graph or Maven catalog."""
    if config.test_mode:
        source = load_test_graph(config.repository)
        require_package(source, config.package)
        return reverse_dependents(
            source, config.package, lambda name: matches(name, config.filter),
        )
    if catalog is None:
        raise ValueError("Для поиска Maven укажите --catalog файл.json")
    target = f"{config.package}:{config.version}"
    repository = Repository(config.repository)

    def excluded(node):
        """Check only the package name, ignoring its version."""
        return matches(node.rsplit(":", 1)[0], config.filter)

    if excluded(target):
        return []
    roots = [target, *load_catalog(catalog)]
    graph = build_graph(
        roots, lambda node: maven_neighbours(repository, node), excluded,
    )
    return reverse_dependents(graph.edges, target, excluded)
