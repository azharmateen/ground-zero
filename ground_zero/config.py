"""Configuration management for ground-zero."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


DEFAULT_CONFIG_PATH = Path.home() / ".ground-zero.yaml"
HISTORY_PATH = Path.home() / ".ground-zero-history.json"


def _load_yaml(filepath: Path) -> dict[str, Any]:
    """Load YAML file, returning empty dict if PyYAML not installed."""
    if yaml is None:
        return {}
    with open(filepath) as f:
        return yaml.safe_load(f) or {}


@dataclass
class Config:
    """User configuration for ground-zero."""

    extra_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)
    global_scan_paths: list[str] = field(default_factory=lambda: ["~/projects", "~/work", "~/dev", "~/code"])
    auto_clean_days: int = 30

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        """Load config from YAML file, falling back to defaults."""
        config_path = path or DEFAULT_CONFIG_PATH
        if config_path.exists():
            try:
                data: dict[str, Any] = _load_yaml(config_path)
                return cls(
                    extra_patterns=data.get("extra_patterns", []),
                    exclude_patterns=data.get("exclude_patterns", []),
                    global_scan_paths=data.get("global_scan_paths", cls().global_scan_paths),
                    auto_clean_days=data.get("auto_clean_days", 30),
                )
            except Exception:
                pass
        return cls()

    def resolved_global_paths(self) -> list[Path]:
        """Return global scan paths with ~ expanded, filtering to existing dirs."""
        paths = []
        for p in self.global_scan_paths:
            expanded = Path(os.path.expanduser(p))
            if expanded.exists() and expanded.is_dir():
                paths.append(expanded)
        return paths

    def is_excluded(self, path: Path) -> bool:
        """Check if a path matches any exclusion pattern."""
        path_str = str(path)
        for pattern in self.exclude_patterns:
            if pattern in path_str:
                return True
        return False
