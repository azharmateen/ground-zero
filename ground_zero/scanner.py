"""Recursive scanner to find cleanable directories."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from .config import Config
from .detector import CleanTarget, classify_target, get_dir_names, get_glob_suffixes


@dataclass
class FoundArtifact:
    """A discovered cleanable artifact on disk."""

    path: Path
    target: CleanTarget
    size_bytes: int = 0
    file_count: int = 0
    project_root: str = ""

    @property
    def size_human(self) -> str:
        """Human-readable size."""
        return _format_size(self.size_bytes)


@dataclass
class ScanResult:
    """Result of a full scan."""

    artifacts: list[FoundArtifact] = field(default_factory=list)
    scan_root: str = ""
    total_dirs_scanned: int = 0

    @property
    def total_size(self) -> int:
        return sum(a.size_bytes for a in self.artifacts)

    @property
    def total_size_human(self) -> str:
        return _format_size(self.total_size)

    def sorted_by_size(self) -> list[FoundArtifact]:
        """Return artifacts sorted by size, largest first."""
        return sorted(self.artifacts, key=lambda a: a.size_bytes, reverse=True)

    def grouped_by_project(self) -> dict[str, list[FoundArtifact]]:
        """Group artifacts by their parent project directory."""
        groups: dict[str, list[FoundArtifact]] = {}
        for a in self.artifacts:
            groups.setdefault(a.project_root, []).append(a)
        return groups

    def grouped_by_ecosystem(self) -> dict[str, list[FoundArtifact]]:
        """Group artifacts by ecosystem type."""
        groups: dict[str, list[FoundArtifact]] = {}
        for a in self.artifacts:
            groups.setdefault(a.target.ecosystem, []).append(a)
        return groups


def _format_size(size_bytes: int) -> str:
    """Format bytes into human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _dir_size(path: Path) -> tuple[int, int]:
    """Calculate total size and file count of a directory."""
    total = 0
    count = 0
    try:
        for dirpath, _dirnames, filenames in os.walk(path):
            for f in filenames:
                try:
                    fp = os.path.join(dirpath, f)
                    total += os.path.getsize(fp)
                    count += 1
                except (OSError, PermissionError):
                    continue
    except (OSError, PermissionError):
        pass
    return total, count


def _infer_project_root(artifact_path: Path) -> str:
    """Infer the project root from an artifact path."""
    return str(artifact_path.parent)


def scan_directory(
    root: Path,
    config: Config | None = None,
    calculate_sizes: bool = True,
    max_depth: int = 10,
) -> ScanResult:
    """Recursively scan a directory for cleanable artifacts."""
    config = config or Config()
    dir_names = get_dir_names(config.extra_patterns)
    glob_suffixes = get_glob_suffixes(config.extra_patterns)
    result = ScanResult(scan_root=str(root))
    _scan_recursive(root, dir_names, glob_suffixes, config, result, calculate_sizes, 0, max_depth)
    return result


def _scan_recursive(
    current: Path,
    dir_names: set[str],
    glob_suffixes: set[str],
    config: Config,
    result: ScanResult,
    calculate_sizes: bool,
    depth: int,
    max_depth: int,
) -> None:
    """Recursively walk the directory tree."""
    if depth > max_depth:
        return

    result.total_dirs_scanned += 1

    try:
        entries = sorted(current.iterdir())
    except (PermissionError, OSError):
        return

    for entry in entries:
        if not entry.is_dir():
            continue

        name = entry.name

        # Check if this is a cleanable target
        is_match = name in dir_names
        if not is_match:
            for suffix in glob_suffixes:
                if name.endswith(suffix):
                    is_match = True
                    break

        if is_match:
            if config.is_excluded(entry):
                continue

            target = classify_target(name, config.extra_patterns)
            if target is None:
                continue

            size_bytes, file_count = (0, 0)
            if calculate_sizes:
                size_bytes, file_count = _dir_size(entry)

            artifact = FoundArtifact(
                path=entry,
                target=target,
                size_bytes=size_bytes,
                file_count=file_count,
                project_root=_infer_project_root(entry),
            )
            result.artifacts.append(artifact)
            # Don't recurse into matched directories
            continue

        # Recurse into non-matched directories
        # Skip hidden dirs (except the ones we're looking for)
        if name.startswith(".") and name not in dir_names:
            continue

        _scan_recursive(entry, dir_names, glob_suffixes, config, result, calculate_sizes, depth + 1, max_depth)
