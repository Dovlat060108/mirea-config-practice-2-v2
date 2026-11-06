"""Maven POM interpretation, HTTP retrieval and readable failures."""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import unittest
from unittest.mock import patch

from maven import MAX_POM_BYTES, Repository, download, pom_url
from pom import expand, parse_pom

BASE = "https://repo.example/maven2"


def pom(body):
    """Wrap a fragment as an XML POM with the official namespace."""
    return (
        '<project xmlns="http://maven.apache.org/POM/4.0.0">'
        '<modelVersion>4.0.0</modelVersion>' + body + '</project>'
    ).encode()


def declaration(artifact="b", version="1", extra=""):
    """Create one test dependency declaration."""
    version_tag = f"<version>{version}</version>" if version else ""
    return (
        f"<dependency><groupId>g</groupId><artifactId>{artifact}</artifactId>"
        f"{version_tag}{extra}</dependency>"
    )


@contextmanager
def repository_server(payloads):
    """Serve POM fixtures on loopback using a real HTTP transport."""
    class Handler(BaseHTTPRequestHandler):
        """Return known POMs and a real 404 for unknown coordinates."""

        def do_GET(self):
            """Respond to one request from the application."""
            data = payloads.get(self.path)
            if data is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            """Keep normal test output quiet."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


class MavenTests(unittest.TestCase):
    """Check direct declarations without calling any package manager."""

    def test_url_layout(self):
        """Use the exact requested version in the standard repository path."""
        url = pom_url(BASE + "/", "org.junit:junit", "4.13.2")
        self.assertEqual(url, BASE + "/org/junit/junit/4.13.2/junit-4.13.2.pom")

    def test_invalid_coordinates(self):
        """Do not allow a package or version to change repository paths."""
        for package, version in (("g:a", "../1"), ("../g:a", "1")):
            with self.subTest(package=package, version=version):
                with self.assertRaises(ValueError):
                    pom_url(BASE, package, version)

    def test_direct_only_with_flags(self):
        """Include test/optional entries; ignore plugins and management."""
        declarations = declaration() + declaration(
            "tests", "2", "<scope>test</scope><optional>true</optional>"
        )
        xml = pom(
            "<dependencies>" + declarations + "</dependencies>"
            "<dependencyManagement><dependencies>" + declaration("managed")
            + "</dependencies></dependencyManagement><build><plugins><plugin>"
            "<dependencies>" + declaration("plugin")
            + "</dependencies></plugin></plugins></build>"
        )
        with patch("maven.download", return_value=xml) as fetch:
            deps = Repository(BASE).direct_dependencies("g:a", "1")
        self.assertEqual([d.artifact for d in deps], ["b", "tests"])
        self.assertEqual(deps[1].scope, "test")
        self.assertIn("optional=true", deps[1].display())
        fetch.assert_called_once()

    def test_properties_and_management(self):
        """Resolve nested properties and a managed version."""
        xml = pom(
            "<properties><base>2</base><dep>${base}.1</dep></properties>"
            "<dependencyManagement><dependencies>"
            + declaration(version="${dep}")
            + "</dependencies></dependencyManagement><dependencies>"
            + declaration(version="") + "</dependencies>"
        )
        with patch("maven.download", return_value=xml):
            deps = Repository(BASE).direct_dependencies("g:a", "1")
        self.assertEqual(deps[0].version, "2.1")

    def test_parent_inheritance_and_child_override(self):
        """Inherit dependencies and managed versions, overriding duplicates."""
        parent = pom(
            "<properties><v>3</v></properties><dependencies>"
            + declaration("inherited") + declaration("override", "1")
            + "</dependencies><dependencyManagement><dependencies>"
            + declaration("managed", "${v}")
            + "</dependencies></dependencyManagement>"
        )
        child = pom(
            "<parent><groupId>g</groupId><artifactId>parent</artifactId>"
            "<version>1</version></parent><dependencies>"
            + declaration("override", "2") + declaration("managed", "")
            + "</dependencies>"
        )
        fixtures = {
            pom_url(BASE, "g:a", "1"): child,
            pom_url(BASE, "g:parent", "1"): parent,
        }
        with patch("maven.download", side_effect=fixtures.__getitem__):
            deps = Repository(BASE).direct_dependencies("g:a", "1")
        versions = {dep.artifact: dep.version for dep in deps}
        self.assertEqual(versions, {"inherited": "1", "override": "2",
                                    "managed": "3"})

    def test_bom_management(self):
        """Use an imported BOM only to supply a declared dependency version."""
        bom = pom("<dependencyManagement><dependencies>"
                  + declaration("b", "7")
                  + "</dependencies></dependencyManagement>")
        child = pom(
            "<dependencyManagement><dependencies>"
            + declaration("bom", "1", "<type>pom</type><scope>import</scope>")
            + "</dependencies></dependencyManagement><dependencies>"
            + declaration(version="") + "</dependencies>"
        )
        fixtures = {
            pom_url(BASE, "g:a", "1"): child,
            pom_url(BASE, "g:bom", "1"): bom,
        }
        with patch("maven.download", side_effect=fixtures.__getitem__):
            deps = Repository(BASE).direct_dependencies("g:a", "1")
        self.assertEqual([dep.version for dep in deps], ["7"])

    def test_empty_and_cache(self):
        """A dependency-free POM remains empty and is downloaded once."""
        repo = Repository(BASE)
        with patch("maven.download", return_value=pom("")) as fetch:
            self.assertEqual(repo.direct_dependencies("g:a", "1"), [])
            self.assertEqual(repo.direct_dependencies("g:a", "1"), [])
        fetch.assert_called_once()

    def test_project_coordinate_property(self):
        """Resolve project.version to the requested package version."""
        xml = pom("<dependencies>" + declaration(version="${project.version}")
                  + "</dependencies>")
        with patch("maven.download", return_value=xml):
            deps = Repository(BASE).direct_dependencies("g:a", "5")
        self.assertEqual(deps[0].version, "5")

    def test_property_errors(self):
        """Reject missing and cyclic properties."""
        for props in ({}, {"v": "${v}"}, {"v": "${w}", "w": "${v}"},
                      {"v": "${v}x"}):
            with self.subTest(properties=props):
                with self.assertRaises(ValueError):
                    expand("${v}", props)

    def test_missing_dependency_fields(self):
        """Require group, artifact and version for each dependency."""
        for body in ("<dependency/>", declaration(version="")):
            with self.subTest(body=body):
                with patch("maven.download", return_value=pom(
                    "<dependencies>" + body + "</dependencies>"
                )):
                    with self.assertRaises(ValueError):
                        Repository(BASE).direct_dependencies("g:a", "1")

    def test_parent_cycle(self):
        """Detect cyclic parent references before a recursive download loop."""
        xml = pom("<parent><groupId>g</groupId><artifactId>a</artifactId>"
                  "<version>1</version></parent>")
        with patch("maven.download", return_value=xml):
            with self.assertRaisesRegex(ValueError, "Цикл"):
                Repository(BASE).direct_dependencies("g:a", "1")

    def test_invalid_pom(self):
        """Report malformed XML and a wrong XML root."""
        for xml in (b"<broken>", b"<html/>"):
            with self.subTest(xml=xml):
                with self.assertRaises(ValueError):
                    parse_pom(xml)

    def test_http_retrieval_and_404(self):
        """Fetch actual HTTP POM responses and report an unavailable version."""
        body = pom("<dependencies>" + declaration() + "</dependencies>")
        with repository_server({"/g/a/1/a-1.pom": body}) as url:
            deps = Repository(url).direct_dependencies("g:a", "1")
            self.assertEqual(deps[0].artifact, "b")
            with self.assertRaisesRegex(ValueError, "HTTP 404"):
                Repository(url).direct_dependencies("g:a", "2")

    def test_download_size_limit(self):
        """Reject an oversized response before parsing XML."""
        with patch("maven.urlopen") as connection:
            response = connection.return_value.__enter__.return_value
            response.read.return_value = b"x" * (MAX_POM_BYTES + 1)
            with self.assertRaisesRegex(ValueError, "размер"):
                download(BASE)


if __name__ == "__main__":
    unittest.main()
