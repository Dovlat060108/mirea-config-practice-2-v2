"""Small Maven POM model built with the Python standard library."""

from dataclasses import dataclass, field
import re
import xml.etree.ElementTree as ET

PROPERTY = re.compile(r"\$\{([^}]+)\}")
MAX_PROPERTY_EXPANSIONS = 1000


def expand(value, properties):
    """Expand nested Maven properties; reject missing values and cycles."""
    seen = set()
    while PROPERTY.search(value):
        if value in seen or len(seen) >= MAX_PROPERTY_EXPANSIONS:
            raise ValueError(f"Цикл свойств POM: {value}")
        seen.add(value)
        match = PROPERTY.search(value)
        name = match.group(1)
        if name not in properties:
            raise ValueError(f"Неизвестное свойство POM: {name}")
        value = value[:match.start()] + properties[name] + value[match.end():]
    return value


def parse_pom(data):
    """Read a namespaced or plain POM, excluding non-project XML."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        raise ValueError(f"Некорректный XML POM: {error}") from error
    for element in root.iter():
        element.tag = element.tag.rsplit("}", 1)[-1]
    if root.tag != "project":
        raise ValueError("POM должен содержать корень project")
    return root


def text(element, name, default=""):
    """Read one immediate child value without searching nested sections."""
    return (element.findtext(name) or default).strip()


def own_properties(root):
    """Extract project properties without interpreting build plugins."""
    section = root.find("properties")
    if section is None:
        return {}
    return {node.tag: (node.text or "").strip() for node in section}


@dataclass(frozen=True)
class Dependency:
    """One direct declaration, including scope and optional status."""

    group: str
    artifact: str
    version: str
    scope: str = "compile"
    optional: str = "false"
    kind: str = "jar"
    classifier: str = ""

    @property
    def key(self):
        """Identify a dependency according to Maven management identity."""
        return self.group, self.artifact, self.kind, self.classifier

    def display(self):
        """Format coordinates with their declared scope and flags."""
        flags = f"scope={self.scope}, optional={self.optional}"
        extra = f", type={self.kind}, classifier={self.classifier or '-'}"
        return f"{self.group}:{self.artifact}:{self.version} [{flags}{extra}]"


@dataclass
class Model:
    """Resolved parent properties, managed versions and direct declarations."""

    properties: dict = field(default_factory=dict)
    management: dict = field(default_factory=dict)
    dependencies: dict = field(default_factory=dict)


def dependency(node, properties, management):
    """Resolve a declaration using properties and dependencyManagement."""
    values = {
        name: expand(text(node, tag), properties)
        for name, tag in (
            ("group", "groupId"), ("artifact", "artifactId"),
            ("version", "version"), ("scope", "scope"),
            ("optional", "optional"), ("kind", "type"),
            ("classifier", "classifier"),
        )
    }
    values["kind"] = values["kind"] or "jar"
    if not values["group"] or not values["artifact"]:
        raise ValueError("Зависимость POM без groupId или artifactId")
    key = tuple(values[name] for name in ("group", "artifact", "kind",
                                           "classifier"))
    managed = management.get(key)
    defaults = {"version": "", "scope": "compile", "optional": "false"}
    for name, default in defaults.items():
        inherited = getattr(managed, name, default)
        values[name] = values[name] or inherited
    if not values["version"]:
        name = f"{values['group']}:{values['artifact']}"
        raise ValueError(f"Не задана версия {name}")
    return Dependency(**values)


def project_properties(root, parent, package, version):
    """Merge parent and child properties and set project coordinate aliases."""
    properties = dict(parent.properties)
    properties.update(own_properties(root))
    group, artifact = package.split(":")
    coordinates = {"groupId": group, "artifactId": artifact, "version": version}
    for name, value in coordinates.items():
        properties[f"project.{name}"] = value
        properties[f"pom.{name}"] = value
    parent_node = root.find("parent")
    if parent_node is not None:
        for name in coordinates:
            value = expand(text(parent_node, name), properties)
            properties[f"project.parent.{name}"] = value
            properties[f"parent.{name}"] = value
    return properties
