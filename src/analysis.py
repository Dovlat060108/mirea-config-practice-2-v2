"""Connect graph traversal to the local or Maven repository."""

from graph import build_graph
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
