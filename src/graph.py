"""Build a dependency graph with recursive depth-first search."""

from dataclasses import dataclass, field


@dataclass
class Graph:
    """Record adjacency lists in DFS order and edges to active ancestors."""

    edges: dict = field(default_factory=dict)
    cycles: list = field(default_factory=list)


def walk(node, neighbours, excluded, graph, active):
    """Visit each node once while retaining edges that close a cycle."""
    if node in graph.edges or excluded(node):
        return
    targets = [target for target in dict.fromkeys(neighbours(node))
               if not excluded(target)]
    graph.edges[node] = targets
    active.add(node)
    for target in targets:
        if target in active:
            graph.cycles.append((node, target))
        else:
            walk(target, neighbours, excluded, graph, active)
    active.remove(node)


def build_graph(roots, neighbours, excluded):
    """Traverse the supplied roots and collect their reachable subgraphs."""
    graph = Graph()
    for root in roots:
        walk(root, neighbours, excluded, graph, set())
    return graph


def reverse_edges(edges):
    """Turn each dependent-to-dependency edge around."""
    incoming = {node: [] for node in edges}
    for node, targets in edges.items():
        for target in targets:
            incoming[target].append(node)
    return incoming


def reverse_dependents(edges, package, excluded):
    """Find all packages reaching the target through the reversed graph."""
    incoming = reverse_edges(edges)
    result = build_graph([package], incoming.get, excluded)
    return [node for node in result.edges if node != package]
