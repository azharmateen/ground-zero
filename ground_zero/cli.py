"""CLI for ground-zero: scan, clean, stats."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from .cleaner import clean_artifacts
from .config import Config
from .detector import get_ecosystems
from .scanner import ScanResult, scan_directory, _format_size
from .stats import Stats, format_history, load_history, record_cleanup


@click.group()
@click.version_option(package_name="ground-zero")
def cli() -> None:
    """ground-zero: The ultimate project cache and artifact cleaner."""


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--global", "global_scan", is_flag=True, help="Scan all configured global paths.")
@click.option("--no-size", is_flag=True, help="Skip size calculation for faster scanning.")
@click.option("--depth", default=10, help="Maximum scan depth.")
@click.option("--ecosystem", "-e", default=None, help="Filter by ecosystem (e.g., Node.js, Python).")
def scan(path: str, global_scan: bool, no_size: bool, depth: int, ecosystem: str | None) -> None:
    """Scan for cleanable artifacts."""
    config = Config.load()

    if global_scan:
        roots = config.resolved_global_paths()
        if not roots:
            click.echo("No valid global scan paths found. Configure in ~/.ground-zero.yaml")
            sys.exit(1)
        click.echo(f"Scanning {len(roots)} global paths...")
        combined = ScanResult(scan_root="global")
        for root in roots:
            click.echo(f"  Scanning {root}...")
            result = scan_directory(root, config, calculate_sizes=not no_size, max_depth=depth)
            combined.artifacts.extend(result.artifacts)
            combined.total_dirs_scanned += result.total_dirs_scanned
        result = combined
    else:
        root = Path(path).resolve()
        click.echo(f"Scanning {root}...")
        result = scan_directory(root, config, calculate_sizes=not no_size, max_depth=depth)

    artifacts = result.artifacts
    if ecosystem:
        artifacts = [a for a in artifacts if a.target.ecosystem.lower() == ecosystem.lower()]

    if not artifacts:
        click.echo("No cleanable artifacts found.")
        return

    # Sort by size (largest first)
    artifacts.sort(key=lambda a: a.size_bytes, reverse=True)

    click.echo(f"\nFound {len(artifacts)} cleanable artifacts:")
    click.echo(f"{'Size':>10s}  {'Type':25s}  Path")
    click.echo("-" * 80)
    for a in artifacts:
        click.echo(f"{a.size_human:>10s}  {a.target.name:25s}  {a.path}")

    click.echo(f"\nTotal reclaimable: {_format_size(sum(a.size_bytes for a in artifacts))}")
    click.echo(f"Directories scanned: {result.total_dirs_scanned}")


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--force", is_flag=True, help="Actually delete (otherwise dry-run).")
@click.option("--parallel", is_flag=True, help="Use parallel deletion for speed.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.option("--ecosystem", "-e", default=None, help="Filter by ecosystem.")
def clean(path: str, force: bool, parallel: bool, yes: bool, ecosystem: str | None) -> None:
    """Clean artifacts (dry-run by default)."""
    config = Config.load()
    root = Path(path).resolve()

    click.echo(f"Scanning {root}...")
    result = scan_directory(root, config)

    artifacts = result.artifacts
    if ecosystem:
        artifacts = [a for a in artifacts if a.target.ecosystem.lower() == ecosystem.lower()]

    if not artifacts:
        click.echo("No cleanable artifacts found.")
        return

    total_size = sum(a.size_bytes for a in artifacts)

    if not force:
        click.echo(f"\n[DRY RUN] Would delete {len(artifacts)} artifacts ({_format_size(total_size)}):")
        for a in sorted(artifacts, key=lambda a: a.size_bytes, reverse=True):
            click.echo(f"  {a.size_human:>10s}  {a.path}")
        click.echo(f"\nRun with --force to actually delete.")
        return

    click.echo(f"\nWill delete {len(artifacts)} artifacts ({_format_size(total_size)}):")
    for a in sorted(artifacts, key=lambda a: a.size_bytes, reverse=True)[:20]:
        click.echo(f"  {a.size_human:>10s}  {a.path}")
    if len(artifacts) > 20:
        click.echo(f"  ... and {len(artifacts) - 20} more")

    if not yes:
        if not click.confirm("\nProceed with deletion?"):
            click.echo("Aborted.")
            return

    click.echo("\nCleaning...")

    def on_progress(artifact, success, error):
        if success:
            click.echo(f"  Deleted: {artifact.path}")
        else:
            click.echo(f"  FAILED:  {artifact.path} ({error})", err=True)

    clean_result = clean_artifacts(
        artifacts,
        dry_run=False,
        parallel=parallel,
        on_progress=on_progress,
    )

    click.echo(f"\nDone! Freed {clean_result.total_freed_human}")
    click.echo(f"  Deleted: {len(clean_result.deleted)}")
    if clean_result.failed:
        click.echo(f"  Failed:  {len(clean_result.failed)}")

    record_cleanup(clean_result.total_freed, len(clean_result.deleted), str(root))


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
@click.option("--top", default=10, help="Number of top directories to show.")
@click.option("--history", is_flag=True, help="Show cleanup history.")
def stats(path: str, top: int, history: bool) -> None:
    """Show disk usage statistics."""
    if history:
        records = load_history()
        click.echo(format_history(records))
        return

    config = Config.load()
    root = Path(path).resolve()

    click.echo(f"Scanning {root}...")
    result = scan_directory(root, config)

    if not result.artifacts:
        click.echo("No cleanable artifacts found.")
        return

    s = Stats.from_scan(result, top_n=top)
    click.echo(f"\n{s.format_report(top_n=top)}")


@cli.command("ecosystems")
def list_ecosystems() -> None:
    """List supported ecosystems and their patterns."""
    ecosystems = get_ecosystems()
    for eco, targets in sorted(ecosystems.items()):
        click.echo(f"\n{eco}:")
        for t in targets:
            glob_marker = " (glob)" if t.is_glob else ""
            click.echo(f"  {t.name:25s}  {t.description}{glob_marker}")


if __name__ == "__main__":
    cli()
