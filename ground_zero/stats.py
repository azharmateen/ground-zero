"""Statistics: reclaimable space, breakdowns, history."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .config import HISTORY_PATH
from .scanner import ScanResult, _format_size


@dataclass
class CleanupRecord:
    """A record of a past cleanup."""

    timestamp: float
    freed_bytes: int
    artifact_count: int
    scan_root: str

    @property
    def freed_human(self) -> str:
        return _format_size(self.freed_bytes)

    @property
    def time_str(self) -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp))


@dataclass
class Stats:
    """Computed statistics from a scan result."""

    total_reclaimable: int = 0
    total_reclaimable_human: str = ""
    artifact_count: int = 0
    by_ecosystem: dict[str, int] = field(default_factory=dict)
    by_type: dict[str, int] = field(default_factory=dict)
    top_dirs: list[tuple[str, int, str]] = field(default_factory=list)

    @classmethod
    def from_scan(cls, result: ScanResult, top_n: int = 10) -> Stats:
        """Build stats from a scan result."""
        stats = cls()
        stats.total_reclaimable = result.total_size
        stats.total_reclaimable_human = result.total_size_human
        stats.artifact_count = len(result.artifacts)

        # By ecosystem
        for eco, arts in result.grouped_by_ecosystem().items():
            stats.by_ecosystem[eco] = sum(a.size_bytes for a in arts)

        # By type (pattern name)
        for a in result.artifacts:
            key = a.target.name
            stats.by_type[key] = stats.by_type.get(key, 0) + a.size_bytes

        # Top N largest
        sorted_arts = result.sorted_by_size()[:top_n]
        stats.top_dirs = [
            (str(a.path), a.size_bytes, a.size_human) for a in sorted_arts
        ]

        return stats

    def format_report(self, top_n: int = 10) -> str:
        """Format stats as a human-readable report."""
        lines = []
        lines.append(f"Total reclaimable space: {self.total_reclaimable_human}")
        lines.append(f"Artifacts found: {self.artifact_count}")
        lines.append("")

        if self.by_ecosystem:
            lines.append("Breakdown by ecosystem:")
            for eco, size in sorted(self.by_ecosystem.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  {eco:20s}  {_format_size(size)}")
            lines.append("")

        if self.by_type:
            lines.append("Breakdown by type:")
            for name, size in sorted(self.by_type.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  {name:25s}  {_format_size(size)}")
            lines.append("")

        if self.top_dirs:
            lines.append(f"Top {min(top_n, len(self.top_dirs))} largest directories:")
            for path, _size, size_human in self.top_dirs[:top_n]:
                lines.append(f"  {size_human:>10s}  {path}")

        return "\n".join(lines)


def record_cleanup(freed_bytes: int, artifact_count: int, scan_root: str) -> None:
    """Record a cleanup to the history file."""
    history = load_history()
    history.append(CleanupRecord(
        timestamp=time.time(),
        freed_bytes=freed_bytes,
        artifact_count=artifact_count,
        scan_root=scan_root,
    ))
    _save_history(history)


def load_history() -> list[CleanupRecord]:
    """Load cleanup history from disk."""
    if not HISTORY_PATH.exists():
        return []
    try:
        with open(HISTORY_PATH) as f:
            data = json.load(f)
        return [CleanupRecord(**r) for r in data]
    except Exception:
        return []


def _save_history(records: list[CleanupRecord]) -> None:
    """Save cleanup history to disk."""
    try:
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_PATH, "w") as f:
            json.dump([asdict(r) for r in records], f, indent=2)
    except Exception:
        pass


def format_history(records: list[CleanupRecord]) -> str:
    """Format history records for display."""
    if not records:
        return "No cleanup history found."
    lines = ["Cleanup history:"]
    total_freed = 0
    for r in records:
        lines.append(f"  {r.time_str}  freed {r.freed_human} ({r.artifact_count} artifacts) in {r.scan_root}")
        total_freed += r.freed_bytes
    lines.append(f"\nTotal freed over all time: {_format_size(total_freed)}")
    return "\n".join(lines)
