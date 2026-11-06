"""Show validation failures for all seven XML settings."""

from pathlib import Path

from config import check_values, read_fields


def main():
    """Print one rejected example per setting, without a network request."""
    folder = Path(__file__).resolve().parent
    valid = read_fields(folder / "junit.xml")
    errors = {
        "package": "junit",
        "repository": "ftp://repo.invalid",
        "test_mode": "yes",
        "version": "../4.13.2",
        "output": "graph.png",
        "ascii_tree": "1",
        "filter": "bad\x01filter",
    }
    for field, value in errors.items():
        try:
            check_values(dict(valid, **{field: value}), folder)
        except ValueError as error:
            print(error)


if __name__ == "__main__":
    main()
