"""Verify the stage 4 reverse mode and its search boundary."""

from contextlib import redirect_stdout
from dataclasses import replace
from io import StringIO
from pathlib import Path
import unittest
from unittest.mock import patch

from analysis import reverse_packages
from config import load_config
from main import main
from pom import Dependency

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class ReverseTests(unittest.TestCase):
    """Check transitive results, cycles and filtering."""

    def test_reverse_cli(self):
        """Find both parents and their ancestors, including outside root A."""
        stream = StringIO()
        with redirect_stdout(stream):
            code = main([str(EXAMPLES / "reverse.xml"), "--reverse"])
        self.assertEqual(code, 0)
        self.assertEqual(
            stream.getvalue().splitlines()[1:], ["B", "A", "E", "C"],
        )

    def test_filtered_ancestor(self):
        """Exclude a parent and nodes reachable only through that parent."""
        config = load_config(EXAMPLES / "reverse.xml")
        self.assertEqual(reverse_packages(replace(config, filter="A")),
                         ["B", "C"])

    def test_isolated_and_self_loop(self):
        """A node is never returned as its own reverse dependency."""
        config = load_config(EXAMPLES / "isolated.xml")
        self.assertEqual(reverse_packages(config), [])
        self.assertEqual(reverse_packages(replace(config, package="G")), [])

    def test_maven_catalog(self):
        """Search a bounded collection of Maven roots and their dependencies."""
        config = load_config(EXAMPLES / "reverse-maven.xml")
        catalog = EXAMPLES / "maven-catalog.json"
        with patch("analysis.Repository") as factory:
            repository = factory.return_value
            repository.direct_dependencies.side_effect = [
                [],
                [Dependency("org.hamcrest", "hamcrest-core", "1.3")],
                [Dependency("junit", "junit", "4.13.2")],
            ]
            result = reverse_packages(config, catalog)
        self.assertEqual(result, ["junit:junit:4.13.2",
                                  "org.slf4j:slf4j-api:2.0.17"])

    def test_maven_requires_catalog(self):
        """Reject unbounded reverse requests with an actionable message."""
        config = load_config(EXAMPLES / "reverse-maven.xml")
        with self.assertRaisesRegex(ValueError, "--catalog"):
            reverse_packages(config)
