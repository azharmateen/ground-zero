"""Detect cleanable directories per ecosystem."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CleanTarget:
    """A directory pattern that can be cleaned."""

    name: str
    ecosystem: str
    description: str
    is_glob: bool = False  # True if name uses glob (e.g., *.egg-info)


# All known cleanable patterns grouped by ecosystem
CLEAN_TARGETS: list[CleanTarget] = [
    # Node.js / JavaScript
    CleanTarget("node_modules", "Node.js", "npm/yarn dependency cache"),
    CleanTarget(".next", "Node.js", "Next.js build output"),
    CleanTarget("dist", "Node.js", "Build output directory"),
    CleanTarget(".nuxt", "Node.js", "Nuxt.js build output"),
    CleanTarget(".output", "Node.js", "Nuxt 3 / Nitro output"),
    CleanTarget(".parcel-cache", "Node.js", "Parcel bundler cache"),
    CleanTarget(".turbo", "Node.js", "Turborepo cache"),
    CleanTarget(".svelte-kit", "Node.js", "SvelteKit build output"),
    CleanTarget(".angular", "Node.js", "Angular build cache"),
    CleanTarget(".expo", "Node.js", "Expo build cache"),
    CleanTarget("storybook-static", "Node.js", "Storybook build output"),
    # Python
    CleanTarget("__pycache__", "Python", "Python bytecode cache"),
    CleanTarget(".pytest_cache", "Python", "Pytest cache"),
    CleanTarget(".mypy_cache", "Python", "Mypy type-check cache"),
    CleanTarget(".ruff_cache", "Python", "Ruff linter cache"),
    CleanTarget(".tox", "Python", "Tox test environment"),
    CleanTarget(".venv", "Python", "Python virtual environment"),
    CleanTarget("venv", "Python", "Python virtual environment"),
    CleanTarget(".egg-info", "Python", "Python package metadata", is_glob=True),
    CleanTarget("htmlcov", "Python", "Coverage HTML report"),
    CleanTarget(".coverage", "Python", "Coverage data file"),
    # Rust
    CleanTarget("target", "Rust", "Cargo build output"),
    # Java / Kotlin / Android
    CleanTarget(".gradle", "Java/Android", "Gradle cache"),
    CleanTarget("build", "Java/Android", "Gradle/Maven build output"),
    # iOS / macOS
    CleanTarget("DerivedData", "iOS", "Xcode derived data"),
    CleanTarget("Pods", "iOS", "CocoaPods dependencies"),
    # Infrastructure
    CleanTarget(".terraform", "Terraform", "Terraform provider cache"),
    CleanTarget(".serverless", "Serverless", "Serverless Framework cache"),
    # General
    CleanTarget(".cache", "General", "Generic cache directory"),
    CleanTarget(".tmp", "General", "Temporary files"),
]


def get_all_patterns(extra: list[str] | None = None) -> list[CleanTarget]:
    """Get all clean targets including user-defined extras."""
    targets = list(CLEAN_TARGETS)
    if extra:
        for pattern in extra:
            targets.append(CleanTarget(pattern, "Custom", "User-defined pattern"))
    return targets


def get_dir_names(extra: list[str] | None = None) -> set[str]:
    """Get the set of directory names to look for (non-glob only)."""
    targets = get_all_patterns(extra)
    return {t.name for t in targets if not t.is_glob}


def get_glob_suffixes(extra: list[str] | None = None) -> set[str]:
    """Get glob suffixes like .egg-info."""
    targets = get_all_patterns(extra)
    return {t.name for t in targets if t.is_glob}


def classify_target(name: str, extra: list[str] | None = None) -> CleanTarget | None:
    """Classify a directory name into a CleanTarget."""
    for t in get_all_patterns(extra):
        if t.is_glob:
            if name.endswith(t.name):
                return t
        else:
            if name == t.name:
                return t
    return None


def get_ecosystems() -> dict[str, list[CleanTarget]]:
    """Group all targets by ecosystem."""
    ecosystems: dict[str, list[CleanTarget]] = {}
    for t in CLEAN_TARGETS:
        ecosystems.setdefault(t.ecosystem, []).append(t)
    return ecosystems
