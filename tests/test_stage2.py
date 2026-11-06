"""Offline graph and stage 2 entry point integration tests."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from main import main
from test_repository import check_graph, direct_test_dependencies

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class StageTwoTests(unittest.TestCase):
    """Verify visible stage 2 output and local repository failures."""

    def test_offline_cli(self):
        """Print only B and C as direct dependencies of A, excluding D."""
        stream = StringIO()
        with redirect_stdout(stream):
            code = main([str(EXAMPLES / "test.xml")])
        self.assertEqual(code, 0)
        self.assertEqual(stream.getvalue().splitlines()[-2:], ["B", "C"])
        self.assertNotIn("test_mode=", stream.getvalue())

    def test_empty_dependencies(self):
        """Explicitly mark a package without direct dependencies."""
        stream = StringIO()
        with patch("main.Repository.direct_dependencies", return_value=[]):
            with redirect_stdout(stream):
                self.assertEqual(main([str(EXAMPLES / "junit.xml")]), 0)
        self.assertIn("(нет)", stream.getvalue())

    def test_network_error_cli(self):
        """Report a dependency retrieval error without a Python traceback."""
        stream = StringIO()
        with patch("main.Repository.direct_dependencies",
                   side_effect=ValueError("HTTP 404")):
            with redirect_stderr(stream):
                self.assertEqual(main([str(EXAMPLES / "junit.xml")]), 2)
        self.assertIn("HTTP 404", stream.getvalue())

    def test_graph_structure_errors(self):
        """Reject invalid graphs and references to absent packages."""
        for graph in ([], {"a": []}, {"A": "B"}, {"A": ["B"]},
                      {"A": [1]}):
            with self.subTest(graph=graph):
                with self.assertRaises(ValueError):
                    check_graph(graph)

    def test_graph_missing_package(self):
        """Report a requested package that is not in the local graph."""
        with self.assertRaisesRegex(ValueError, "нет пакета"):
            direct_test_dependencies(EXAMPLES / "graph.json", "Z")

    def test_graph_read_errors(self):
        """Handle missing and malformed JSON with a readable diagnostic."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            with self.assertRaises(ValueError):
                direct_test_dependencies(path, "A")
            path.write_text("{")
            with self.assertRaises(ValueError):
                direct_test_dependencies(path, "A")


if __name__ == "__main__":
    unittest.main()
