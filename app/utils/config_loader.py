#app/utils/config_loader.py


import tomllib
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ScraperTarget:
    name: str
    url: str
    location_filter: str
    enabled: bool = True


def load_targets(path: str | Path = "targets.toml") -> list[ScraperTarget]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path.resolve()}")

    with open(path, "rb") as f:  # tomllib requires binary mode
        data = tomllib.load(f)

    targets = data.get("targets", [])
    if not targets:
        raise ValueError("No [[targets]] defined in targets.toml")

    return [
        ScraperTarget(
            name=t["name"],
            url=t["url"],
            location_filter=t.get("location_filter", ""),
            enabled=t.get("enabled", True),
        )
        for t in targets
    ]


def load_active_targets(path: str | Path = "targets.toml") -> list[ScraperTarget]:
    return [t for t in load_targets(path) if t.enabled]