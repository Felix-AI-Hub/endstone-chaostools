import json
from pathlib import Path


class JsonStore:
    """A dict that is kept in a JSON file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: dict[str, dict] = (
            json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        )

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
