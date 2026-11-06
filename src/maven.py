"""Retrieve POM documents over HTTP(S), without Maven or third-party tools."""

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config import check_package, check_repository, VERSION_PATTERN
from pom import (
    Model, dependency, expand, own_properties, parse_pom, project_properties,
    text,
)
import re

TIMEOUT_SECONDS = 15
MAX_POM_BYTES = 4 * 1024 * 1024


def pom_url(repository, package, version):
    """Convert exact group:artifact:version coordinates to a Maven POM URL."""
    check_repository(repository)
    check_package(package, False)
    if not re.fullmatch(VERSION_PATTERN, version):
        raise ValueError("Нужна точная версия POM без слешей и пробелов")
    group, artifact = package.split(":")
    folder = group.replace(".", "/")
    return (
        f"{repository.rstrip('/')}/{folder}/{artifact}/{version}/"
        f"{artifact}-{version}.pom"
    )


def download(url):
    """Read a bounded POM response; turn transport failures into diagnostics."""
    request = Request(url, headers={"User-Agent": "mirea-pr2-variant2/1.0"})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = response.read(MAX_POM_BYTES + 1)
    except HTTPError as error:
        raise ValueError(f"HTTP {error.code}: POM недоступен: {url}") from error
    except (URLError, OSError) as error:
        raise ValueError(f"Ошибка загрузки POM: {error}") from error
    if len(data) > MAX_POM_BYTES:
        raise ValueError("POM превышает допустимый размер")
    return data


class Repository:
    """Load parents and BOM imports with caching and cycle checks."""

    def __init__(self, url):
        """Bind all model requests to the configured repository."""
        check_repository(url)
        self.url = url
        self.cache = {}

    def parent_model(self, root, trail):
        """Fetch the parent from the configured repository."""
        node = root.find("parent")
        if node is None:
            return Model()
        properties = own_properties(root)
        group = expand(text(node, "groupId"), properties)
        artifact = expand(text(node, "artifactId"), properties)
        version = expand(text(node, "version"), properties)
        return self.model(f"{group}:{artifact}", version, trail)

    def managed_dependencies(self, root, parent, properties, trail):
        """Merge inherited management, imported BOMs and local declarations."""
        managed = dict(parent.management)
        local = {}
        imported = {}
        nodes = root.findall("dependencyManagement/dependencies/dependency")
        for node in nodes:
            dep = dependency(node, properties, managed)
            if dep.scope == "import" and dep.kind == "pom":
                package = f"{dep.group}:{dep.artifact}"
                bom = self.model(package, dep.version, trail)
                for key, value in bom.management.items():
                    imported.setdefault(key, value)
            else:
                local[dep.key] = dep
        managed.update(imported)
        managed.update(local)
        return managed

    def model(self, package, version, trail=()):
        """Resolve a POM's direct dependencies, parent and managed versions."""
        coordinate = package, version
        if coordinate in trail:
            raise ValueError(f"Цикл parent/BOM: {package}:{version}")
        if coordinate in self.cache:
            return self.cache[coordinate]
        trail = trail + (coordinate,)
        root = parse_pom(download(pom_url(self.url, package, version)))
        parent = self.parent_model(root, trail)
        properties = project_properties(root, parent, package, version)
        management = self.managed_dependencies(root, parent, properties, trail)
        dependencies = dict(parent.dependencies)
        for node in root.findall("dependencies/dependency"):
            dep = dependency(node, properties, management)
            dependencies[dep.key] = dep
        model = Model(properties, management, dependencies)
        self.cache[coordinate] = model
        return model

    def direct_dependencies(self, package, version):
        """Return direct declarations without traversing their dependencies."""
        model = self.model(package, version)
        return list(model.dependencies.values())
