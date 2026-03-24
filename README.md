# ground-zero

[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-blue?logo=anthropic&logoColor=white)](https://claude.ai/code)


The ultimate project cache and artifact cleaner. Detect and nuke `node_modules`, `__pycache__`, `.next`, `build`, and dozens more across all your projects.

## Installation

```bash
pip install ground-zero
```

## Usage

```bash
# Scan current directory for cleanable artifacts
ground-zero scan

# Scan with global paths (home directory projects)
ground-zero scan --global

# Clean artifacts (dry-run by default)
ground-zero clean

# Actually delete (requires confirmation)
ground-zero clean --force

# Parallel deletion for speed
ground-zero clean --force --parallel

# Show disk usage stats
ground-zero stats

# Show top 20 largest directories
ground-zero stats --top 20
```

## Supported Ecosystems

| Ecosystem | Detected Directories |
|-----------|---------------------|
| Node.js | `node_modules`, `.next`, `dist`, `build`, `.nuxt`, `.output`, `.parcel-cache`, `.turbo` |
| Python | `__pycache__`, `.pytest_cache`, `*.egg-info`, `.mypy_cache`, `.venv`, `.ruff_cache`, `.tox` |
| Rust | `target` |
| Java | `target`, `.gradle`, `build` |
| iOS | `DerivedData`, `Pods` |
| Terraform | `.terraform` |
| General | `.cache`, `.tmp` |

## Configuration

Create `~/.ground-zero.yaml` to customize:

```yaml
extra_patterns:
  - ".sass-cache"
  - ".parcel-cache"
exclude_patterns:
  - "important-project/node_modules"
global_scan_paths:
  - ~/projects
  - ~/work
auto_clean_days: 30
```

## License

MIT
