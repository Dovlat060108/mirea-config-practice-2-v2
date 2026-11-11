"""Check observable DFS behaviour on cyclic and filtered graphs."""

from collections import Counter
from dataclasses import replace
from pathlib import Path
import unittest

from analysis import forward_graph, maven_neighbours
from config import load_config
from graph import build_graph

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class GraphTests(unittest.TestCase):
    """Exercise graph traversal and Maven scope selection."""

    def test_diamond_and_cycle(self):
        """Keep both incoming edges but load the shared node only once."""
        edges = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": ["B"]}
        calls = Counter()

        def neighbours(node):
            """Record repository reads for this traversal."""
            calls[node] += 1
            return edges[node]

        result = build_graph(["A"], neighbours, lambda node: False)
        self.assertEqual(list(result.edges), ["A", "B", "D", "C"])
        self.assertEqual(result.edges, edges)
        self.assertEqual(result.cycles, [("D", "B")])
        self.assertEqual(calls, Counter(edges.keys()))

    def test_filter_prunes_descendants(self):
        """Skip a filtered node and packages reachable only through it."""
        config = load_config(EXAMPLES / "graph-cycles.xml")
        result = forward_graph(config)
        self.assertEqual(result.edges["A"], ["B", "C"])
        self.assertNotIn("BX", result.edges)
        self.assertNotIn("Z", result.edges)
        self.assertIn("D", result.edges)

    def test_filter_can_exclude_root(self):
        """An excluded starting package has an empty result."""
        config = load_config(EXAMPLES / "test.xml")
        self.assertEqual(forward_graph(replace(config, filter="A")).edges, {})

    def test_self_loop(self):
        """A self-reference produces an edge and terminates."""
        config = load_config(EXAMPLES / "graph-cycles.xml")
        result = forward_graph(replace(config, package="G"))
        self.assertEqual(result.edges, {"G": ["G"]})
        self.assertEqual(result.cycles, [("G", "G")])

    def test_maven_scope(self):
        """Traverse compile/runtime and omit test and optional declarations."""
        from unittest.mock import Mock
        from pom import Dependency

        repository = Mock()
        repository.direct_dependencies.return_value = [
            Dependency("g", "compile", "1"),
            Dependency("g", "runtime", "2", scope="runtime"),
            Dependency("g", "test", "3", scope="test"),
            Dependency("g", "extra", "4", optional="true"),
        ]
        result = maven_neighbours(repository, "g:root:5")
        self.assertEqual(result, ["g:compile:1", "g:runtime:2"])
        repository.direct_dependencies.assert_called_once_with("g:root", "5")
