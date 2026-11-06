"""Read and validate the XML application configuration."""

from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

FIELDS = (
    "package", "repository", "test_mode", "version", "output",
    "ascii_tree", "filter",
)
PACKAGE_PATTERN = r"[A-Za-z0-9_][A-Za-z0-9_.-]*"
VERSION_PATTERN = r"[A-Za-z0-9_][A-Za-z0-9_.+-]*"


@dataclass(frozen=True)
class Config:
    """Seven settings of variant 2; paths are relative to the XML file."""

    package: str
    repository: str
    test_mode: bool
    version: str
    output: str
    ascii_tree: bool
    filter: str


def parse_bool(value, name):
    """Accept only explicit XML boolean values true and false."""
    if value not in ("true", "false"):
        raise ValueError(f"{name}: ожидается true или false")
    return value == "true"


def check_package(package, test_mode):
    """Validate a Maven group:artifact coordinate or a test graph name."""
    if test_mode:
        valid = re.fullmatch(r"[A-Z]+", package)
    else:
        valid = re.fullmatch(
            f"{PACKAGE_PATTERN}:{PACKAGE_PATTERN}", package
        )
    if not valid:
        raise ValueError("package: нужно groupId:artifactId или A в тесте")


def check_repository(value):
    """Require a complete HTTP(S) repository URL without credentials."""
    try:
        url = urlsplit(value)
        valid = url.scheme in ("http", "https") and url.hostname
        valid = valid and not (url.username or url.password)
        valid = valid and not (url.query or url.fragment)
        url.port
    except ValueError as error:
        raise ValueError("repository: некорректный URL") from error
    if not valid or any(char.isspace() for char in value):
        raise ValueError("repository: нужен HTTP(S) URL без параметров")


def collect_fields(root):
    """Validate the XML shape and collect the seven text fields."""
    if root.tag != "config" or root.attrib:
        raise ValueError("XML: корневой элемент должен быть <config>")
    values = {}
    for child in root:
        if child.tag not in FIELDS or child.tag in values:
            raise ValueError(f"XML: лишнее или повторное поле {child.tag}")
        if len(child) or child.attrib:
            raise ValueError(f"XML: поле {child.tag} должно содержать текст")
        values[child.tag] = (child.text or "").strip()
    missing = set(FIELDS) - values.keys()
    if missing:
        raise ValueError("XML: отсутствуют поля " + ", ".join(sorted(missing)))
    return values


def read_fields(path):
    """Reject malformed XML, unknown tags, duplicates and missing values."""
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as error:
        raise ValueError(f"Не удалось прочитать XML: {error}") from error
    return collect_fields(root)


def check_values(values, base):
    """Validate every user setting without creating output files."""
    test_mode = parse_bool(values["test_mode"], "test_mode")
    parse_bool(values["ascii_tree"], "ascii_tree")
    check_package(values["package"], test_mode)
    if not re.fullmatch(VERSION_PATTERN, values["version"]):
        raise ValueError("version: нужна версия без слешей и пробелов")
    if test_mode:
        if not (base / values["repository"]).is_file():
            raise ValueError("repository: файл тестового репозитория не найден")
    else:
        check_repository(values["repository"])
    output = Path(values["output"])
    if output.suffix.lower() != ".svg" or output.name == ".svg":
        raise ValueError("output: нужно имя файла с расширением .svg")
    if (base / output).is_dir():
        raise ValueError("output: указан каталог вместо файла")
    if not (base / output).parent.is_dir():
        raise ValueError("output: родительский каталог не существует")
    if any(ord(char) < ord(" ") for char in values["filter"]):
        raise ValueError("filter: управляющие символы запрещены")


def load_config(filename):
    """Return validated settings, resolving local paths from the XML folder."""
    path = Path(filename).resolve()
    values = read_fields(path)
    check_values(values, path.parent)
    values["test_mode"] = parse_bool(values["test_mode"], "test_mode")
    values["ascii_tree"] = parse_bool(values["ascii_tree"], "ascii_tree")
    if values["test_mode"]:
        repository = path.parent / values["repository"]
        values["repository"] = str(repository.resolve())
    values["output"] = str((path.parent / values["output"]).resolve())
    return Config(**values)


def display_config(config, stream):
    """Print all seven settings in a stable key=value format."""
    for name in FIELDS:
        value = getattr(config, name)
        if isinstance(value, bool):
            value = str(value).lower()
        print(f"{name}={value}", file=stream)
