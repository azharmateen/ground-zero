"""Predefined and custom cleanup profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .detector import CleanTarget, CLEAN_TARGETS


@dataclass
class Profile:
    """A named set of cleanup patterns."""

    name: str
    description: str
    ecosystems: list[str] = field(default_factory=list)
    extra_patterns: list[str] = field(default_factory=list)

    def get_targets(self) -> list[CleanTarget]:
        """Get all CleanTarget entries matching this profile."""
        targets = []
        eco_set = {e.lower() for e in self.ecosystems}
        for t in CLEAN_TARGETS:
            if t.ecosystem.lower() in eco_set:
                targets.append(t)
        for pattern in self.extra_patterns:
            targets.append(CleanTarget(pattern, "Custom", f"Custom pattern from profile '{self.name}'"))
        return targets

    def get_dir_names(self) -> set[str]:
        """Get directory names to match for this profile."""
        return {t.name for t in self.get_targets() if not t.is_glob}

    def get_glob_suffixes(self) -> set[str]:
        """Get glob suffixes to match for this profile."""
        return {t.name for t in self.get_targets() if t.is_glob}


# Built-in profiles
BUILTIN_PROFILES: dict[str, Profile] = {
    "web-dev": Profile(
        name="web-dev",
        description="Frontend/fullstack JS/TS development",
        ecosystems=["Node.js"],
    ),
    "python": Profile(
        name="python",
        description="Python development (caches, venvs, test artifacts)",
        ecosystems=["Python"],
    ),
    "mobile": Profile(
        name="mobile",
        description="iOS and Android development",
        ecosystems=["iOS", "Java/Android", "Node.js"],
    ),
    "rust": Profile(
        name="rust",
        description="Rust/Cargo development",
        ecosystems=["Rust"],
    ),
    "java": Profile(
        name="java",
        description="Java/Kotlin/Gradle development",
        ecosystems=["Java/Android"],
    ),
    "devops": Profile(
        name="devops",
        description="Infrastructure and DevOps tools",
        ecosystems=["Terraform", "Serverless"],
    ),
    "all": Profile(
        name="all",
        description="Everything -- all ecosystems",
        ecosystems=[
            "Node.js", "Python", "Rust", "Java/Android", "iOS",
            "Terraform", "Serverless", "General",
        ],
    ),
}


def get_profile(name: str) -> Profile | None:
    """Get a built-in profile by name."""
    return BUILTIN_PROFILES.get(name.lower())


def list_profiles() -> list[Profile]:
    """List all built-in profiles."""
    return list(BUILTIN_PROFILES.values())


def load_custom_profiles(config_path: Path | None = None) -> dict[str, Profile]:
    """Load custom profiles from .ground-zero.yaml."""
    if config_path is None:
        config_path = Path.home() / ".ground-zero.yaml"

    if not config_path.exists():
        return {}

    try:
        import yaml
    except ImportError:
        return {}

    try:
        with open(config_path) as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
    except Exception:
        return {}

    custom: dict[str, Profile] = {}
    for name, pdata in data.get("profiles", {}).items():
        if isinstance(pdata, dict):
            custom[name] = Profile(
                name=name,
                description=pdata.get("description", f"Custom profile: {name}"),
                ecosystems=pdata.get("ecosystems", []),
                extra_patterns=pdata.get("extra_patterns", []),
            )
    return custom


def get_all_profiles() -> dict[str, Profile]:
    """Get all profiles: built-in + custom (custom overrides built-in)."""
    profiles = dict(BUILTIN_PROFILES)
    profiles.update(load_custom_profiles())
    return profiles
