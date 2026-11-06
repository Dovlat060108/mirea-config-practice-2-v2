"""Configuration validation and command line behaviour."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest

from config import (
    FIELDS, check_values, display_config, load_config, read_fields,
)
from main import main

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class ConfigTests(unittest.TestCase):
    """Exercise valid XML and failures for each configurable field."""

    def test_real_config(self):
        """Read all real Maven settings."""
        config = load_config(EXAMPLES / "junit.xml")
        self.assertEqual(config.package, "junit:junit")
        self.assertFalse(config.test_mode)
        self.assertEqual(config.version, "4.13.2")
        self.assertEqual(config.filter, "")

    def test_test_config_relative_paths(self):
        """Resolve local paths relative to XML, not the working directory."""
        config = load_config(EXAMPLES / "test.xml")
        self.assertTrue(config.test_mode)
        self.assertTrue(config.ascii_tree)
        self.assertEqual(Path(config.repository), EXAMPLES / "graph.json")

    def test_each_field_error(self):
        """Reject one invalid value for every setting."""
        errors = {
            "package": "bad", "repository": "file:///tmp/pom",
            "test_mode": "yes", "version": "../1", "output": "a.png",
            "ascii_tree": "1", "filter": "x\x01",
        }
        values = read_fields(EXAMPLES / "junit.xml")
        for key, value in errors.items():
            with self.subTest(field=key):
                with self.assertRaisesRegex(ValueError, key):
                    check_values(dict(values, **{key: value}), EXAMPLES)

    def test_url_errors(self):
        """Reject partial, authenticated and malformed repository URLs."""
        values = read_fields(EXAMPLES / "junit.xml")
        urls = (
            "https:///missing", "https://user:pass@example.org",
            "https://example.org?q=1", "https://example.org/#x",
            "https://example.org:wrong", "https://exa mple.org",
        )
        for url in urls:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    check_values(dict(values, repository=url), EXAMPLES)

    def test_missing_test_repository(self):
        """Check file existence when test mode is enabled."""
        values = read_fields(EXAMPLES / "test.xml")
        with self.assertRaisesRegex(ValueError, "repository"):
            check_values(dict(values, repository="absent.json"), EXAMPLES)

    def test_output_directory(self):
        """Reject an absent destination folder and a directory named .svg."""
        values = read_fields(EXAMPLES / "junit.xml")
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / "folder.svg").mkdir()
            for output in ("absent/graph.svg", "folder.svg", ".svg"):
                with self.subTest(output=output):
                    with self.assertRaisesRegex(ValueError, "output"):
                        check_values(dict(values, output=output), base)

    def test_xml_structure_errors(self):
        """Reject unknown, nested, duplicate, missing and malformed tags."""
        text = (EXAMPLES / "junit.xml").read_text()
        variants = (
            "<broken>", text.replace("config>", "wrong>"),
            text.replace("</config>", "<extra>x</extra></config>"),
            text.replace("</config>", "<version>1</version></config>"),
            text.replace("<filter></filter>", ""),
            text.replace("<filter></filter>", "<filter><x/></filter>"),
            text.replace("<filter>", '<filter value="x">'),
        )
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.xml"
            for xml in variants:
                path.write_text(xml)
                with self.subTest(xml=xml[:30]):
                    with self.assertRaises(ValueError):
                        load_config(path)

    def test_missing_xml(self):
        """Report missing configuration as a readable error."""
        with self.assertRaisesRegex(ValueError, "XML"):
            load_config(EXAMPLES / "absent.xml")

    def test_cli_error(self):
        """Return an error code and no traceback."""
        stream = StringIO()
        with redirect_stderr(stream):
            code = main([str(EXAMPLES / "absent.xml")])
        self.assertEqual(code, 2)
        self.assertIn("Ошибка:", stream.getvalue())

    def test_display_all_settings(self):
        """Print exactly seven key=value lines including an empty filter."""
        stream = StringIO()
        display_config(load_config(EXAMPLES / "junit.xml"), stream)
        lines = stream.getvalue().splitlines()
        self.assertEqual([line.split("=")[0] for line in lines], list(FIELDS))
        self.assertIn("test_mode=false", lines)
        self.assertIn("filter=", lines)


if __name__ == "__main__":
    unittest.main()
