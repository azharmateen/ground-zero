"""Safe cleanup with dry-run, confirmation, and parallel deletion."""

from __future__ import annotations

import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .scanner import FoundArtifact, _format_size


@dataclass
class CleanResult:
    """Result of a cleanup operation."""

    deleted: list[FoundArtifact] = field(default_factory=list)
    failed: list[tuple[FoundArtifact, str]] = field(default_factory=list)
    skipped: list[FoundArtifact] = field(default_factory=list)

    @property
    def total_freed(self) -> int:
        return sum(a.size_bytes for a in self.deleted)

    @property
    def total_freed_human(self) -> str:
        return _format_size(self.total_freed)


def _has_gitkeep(path: Path) -> bool:
    """Check if directory contains a .gitkeep file."""
    try:
        for entry in path.iterdir():
            if entry.name == ".gitkeep":
                return True
    except (PermissionError, OSError):
        pass
    return False


def _delete_single(artifact: FoundArtifact) -> tuple[FoundArtifact, str | None]:
    """Delete a single artifact directory. Returns (artifact, error_or_none)."""
    try:
        if _has_gitkeep(artifact.path):
            # Preserve .gitkeep -- delete everything else
            for entry in artifact.path.iterdir():
                if entry.name == ".gitkeep":
                    continue
                if entry.is_dir():
                    shutil.rmtree(entry, ignore_errors=True)
                else:
                    entry.unlink(missing_ok=True)
        else:
            shutil.rmtree(artifact.path)
        return (artifact, None)
    except Exception as e:
        return (artifact, str(e))


def clean_artifacts(
    artifacts: list[FoundArtifact],
    dry_run: bool = True,
    parallel: bool = False,
    max_workers: int = 4,
    on_progress: Callable[[FoundArtifact, bool, str | None], None] | None = None,
) -> CleanResult:
    """Clean the given artifacts.

    Args:
        artifacts: List of artifacts to clean.
        dry_run: If True, don't actually delete anything.
        parallel: If True, use thread pool for parallel deletion.
        max_workers: Max threads for parallel mode.
        on_progress: Callback(artifact, success, error) for each item.

    Returns:
        CleanResult with deleted/failed/skipped lists.
    """
    result = CleanResult()

    if dry_run:
        result.skipped = list(artifacts)
        return result

    if parallel and len(artifacts) > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_delete_single, a): a for a in artifacts}
            for future in as_completed(futures):
                artifact, error = future.result()
                if error:
                    result.failed.append((artifact, error))
                    if on_progress:
                        on_progress(artifact, False, error)
                else:
                    result.deleted.append(artifact)
                    if on_progress:
                        on_progress(artifact, True, None)
    else:
        for artifact in artifacts:
            artifact, error = _delete_single(artifact)
            if error:
                result.failed.append((artifact, error))
                if on_progress:
                    on_progress(artifact, False, error)
            else:
                result.deleted.append(artifact)
                if on_progress:
                    on_progress(artifact, True, None)

    return result
