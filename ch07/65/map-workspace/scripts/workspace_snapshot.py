#!/usr/bin/env python3
"""Build and compare safe workspace snapshots for the map-workspace skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime
from typing import Any, Iterable


SCHEMA_VERSION = 1
DEFAULT_GUIDE = "WORKSPACE_GUIDE.md"
DEFAULT_STATE = ".codex/workspace-guide-state.json"
MAX_HASH_BYTES = 1_000_000
MAX_FILES = 50_000

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "target",
    "coverage",
    ".coverage",
    ".cache",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
}

EVIDENCE_NAMES = {
    "agents.md",
    "contributing.md",
    "contributing.rst",
    "contributing.txt",
    "package.json",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "tox.ini",
    "cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
    "makefile",
    "gnumakefile",
    "justfile",
    "taskfile.yml",
    "taskfile.yaml",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
    "gemfile",
    "mix.exs",
    "deno.json",
    "deno.jsonc",
    "project.clj",
    "composer.json",
    "workspace.json",
    "nx.json",
    "turbo.json",
    "lerna.json",
}

LOCKFILE_NAMES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lock",
    "bun.lockb",
    "poetry.lock",
    "uv.lock",
    "pdm.lock",
    "cargo.lock",
    "gemfile.lock",
    "composer.lock",
}

ENTRY_NAMES = {
    "main.py",
    "app.py",
    "manage.py",
    "wsgi.py",
    "asgi.py",
    "main.go",
    "main.rs",
    "index.js",
    "index.ts",
    "server.js",
    "server.ts",
    "program.cs",
    "application.java",
}

SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".jks", ".keystore"}
SENSITIVE_EXACT = {
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    ".npmrc",
    ".pypirc",
    "credentials",
    "credentials.json",
    "secrets.json",
}


class SnapshotError(RuntimeError):
    """A user-facing snapshot error."""


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(128 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_bytes(encoded.encode("utf-8"))


def relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_root(raw: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise SnapshotError("--root must be an absolute path")
    path = path.resolve()
    if not path.is_dir():
        raise SnapshotError(f"workspace root is not an existing directory: {path}")
    return path


def resolve_inside(root: Path, raw: str, label: str) -> Path:
    candidate = Path(raw)
    path = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    if not is_relative_to(path, root):
        raise SnapshotError(f"{label} must stay inside the workspace root")
    return path


def is_sensitive(rel: str) -> bool:
    path = Path(rel)
    name = path.name.lower()
    if name.startswith(".env"):
        return not any(token in name for token in ("example", "sample", "template"))
    if name in SENSITIVE_EXACT or path.suffix.lower() in SENSITIVE_SUFFIXES:
        return True
    return name.endswith((".secret", ".secrets", ".token", ".credentials"))


def is_evidence(rel: str) -> bool:
    path = Path(rel)
    name = path.name.lower()
    parts = [part.lower() for part in path.parts]
    if name.startswith(".env") and any(
        token in name for token in ("example", "sample", "template")
    ):
        return True
    if name.startswith("readme") or name.startswith("contributing"):
        return path.suffix.lower() in {"", ".md", ".rst", ".txt"}
    if name in EVIDENCE_NAMES:
        return True
    if name.startswith(("requirements", "docker-compose", "compose")):
        return path.suffix.lower() in {".txt", ".in", ".yml", ".yaml"}
    if ".github" in parts and "workflows" in parts:
        return path.suffix.lower() in {".yml", ".yaml"}
    if "docs" in parts and path.suffix.lower() in {".md", ".rst", ".txt"}:
        return True
    if name.endswith((".csproj", ".fsproj", ".vbproj", ".sln")):
        return True
    return False


def is_entry_candidate(rel: str) -> bool:
    path = Path(rel)
    name = path.name.lower()
    if name in ENTRY_NAMES:
        return True
    parts = [part.lower() for part in path.parts]
    return name in {"__main__.py", "cli.py"} or (
        "src" in parts and name.startswith(("main.", "index.", "app.", "server."))
    )


def run_git(root: Path, args: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        ["git", "-C", str(root), "-c", "core.quotepath=false", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    if check and process.returncode != 0:
        raise SnapshotError(process.stderr.strip() or "git command failed")
    return process


def status_path(line: str, root: Path, top: Path) -> str | None:
    value = line[3:] if len(line) >= 4 else line
    if " -> " in value:
        value = value.split(" -> ", 1)[1]
    value = value.strip().strip('"')
    candidate = (top / value).resolve()
    if is_relative_to(candidate, root):
        return relative_posix(candidate, root)
    return None


def git_context(root: Path, excluded: set[str]) -> dict[str, Any] | None:
    try:
        inside = run_git(root, ["rev-parse", "--is-inside-work-tree"])
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return None

    top_result = run_git(root, ["rev-parse", "--show-toplevel"], check=True)
    top = Path(top_result.stdout.strip()).resolve()
    head_result = run_git(root, ["rev-parse", "HEAD"])
    branch_result = run_git(root, ["branch", "--show-current"])
    status_result = run_git(root, ["status", "--porcelain=v1", "--untracked-files=all", "--", "."])
    commit_result = run_git(root, ["log", "-1", "--format=%h%x09%cI%x09%s"])
    raw_status = [line for line in status_result.stdout.splitlines() if line.strip()]
    status_lines = [
        line for line in raw_status if status_path(line, root, top) not in excluded
    ]
    return {
        "top": str(top),
        "head": head_result.stdout.strip() if head_result.returncode == 0 else None,
        "branch": branch_result.stdout.strip() or None,
        "status": status_lines,
        "status_digest": json_digest(status_lines),
        "last_commit": commit_result.stdout.strip() if commit_result.returncode == 0 else None,
    }


def git_visible_files(root: Path, git: dict[str, Any]) -> list[Path] | None:
    result = run_git(root, ["ls-files", "--cached", "--others", "--exclude-standard", "--", "."])
    if result.returncode != 0:
        return None
    top = Path(git["top"])
    paths: list[Path] = []
    for raw in result.stdout.splitlines():
        candidate = (top / raw).resolve()
        if is_relative_to(candidate, root) and candidate.exists():
            paths.append(candidate)
    return paths


def walk_visible_files(root: Path, warnings: list[str]) -> tuple[list[Path], list[str]]:
    paths: list[Path] = []
    symlinks: list[str] = []
    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept_dirs: list[str] = []
        for directory in sorted(dirs):
            candidate = current_path / directory
            rel = relative_posix(candidate, root)
            if candidate.is_symlink():
                symlinks.append(rel)
            elif directory.lower() not in SKIP_DIRS:
                kept_dirs.append(directory)
        dirs[:] = kept_dirs
        for filename in sorted(files):
            candidate = current_path / filename
            paths.append(candidate)
            if len(paths) >= MAX_FILES:
                warnings.append(f"file inventory truncated at {MAX_FILES} entries")
                return paths, symlinks
    return paths, symlinks


def discover_sensitive_and_symlinks(root: Path) -> tuple[list[str], list[str]]:
    """Inspect names only so ignored secrets are reported without reading their contents."""
    sensitive: list[str] = []
    symlinks: list[str] = []
    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept_dirs: list[str] = []
        for directory in sorted(dirs):
            candidate = current_path / directory
            rel = relative_posix(candidate, root)
            if candidate.is_symlink():
                symlinks.append(rel)
            elif directory.lower() not in SKIP_DIRS:
                kept_dirs.append(directory)
        dirs[:] = kept_dirs
        for filename in files:
            candidate = current_path / filename
            rel = relative_posix(candidate, root)
            if candidate.is_symlink():
                symlinks.append(rel)
            if is_sensitive(rel):
                sensitive.append(rel)
    return sensitive, symlinks


def collect_snapshot(root: Path, excluded: set[str] | None = None) -> dict[str, Any]:
    excluded = excluded or set()
    warnings: list[str] = []
    git = git_context(root, excluded)
    symlinks: list[str] = []
    paths = git_visible_files(root, git) if git else None
    if paths is None:
        paths, symlinks = walk_visible_files(root, warnings)
    name_only_sensitive, name_only_symlinks = discover_sensitive_and_symlinks(root)
    symlinks.extend(name_only_symlinks)

    inventory: dict[str, dict[str, Any]] = {}
    evidence_hashes: dict[str, str] = {}
    evidence_files: list[str] = []
    entry_candidates: list[str] = []
    sensitive_paths: list[str] = list(name_only_sensitive)
    lockfiles: list[str] = []
    top_directories: set[str] = set()

    for path in sorted(set(paths), key=lambda item: str(item).lower()):
        try:
            rel = relative_posix(path, root)
            stat = path.lstat()
        except (FileNotFoundError, OSError, ValueError) as exc:
            warnings.append(f"could not inspect {path}: {exc}")
            continue
        if rel in excluded:
            continue
        if path.is_symlink():
            symlinks.append(rel)
            inventory[rel] = {"type": "symlink", "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
            continue
        if not path.is_file():
            continue
        inventory[rel] = {"type": "file", "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
        if len(Path(rel).parts) > 1:
            top_directories.add(Path(rel).parts[0])
        if is_sensitive(rel):
            sensitive_paths.append(rel)
            continue
        if Path(rel).name.lower() in LOCKFILE_NAMES:
            lockfiles.append(rel)
        if is_evidence(rel):
            evidence_files.append(rel)
            if stat.st_size <= MAX_HASH_BYTES:
                try:
                    evidence_hashes[rel] = sha256_file(path)
                except OSError as exc:
                    warnings.append(f"could not hash {rel}: {exc}")
            else:
                warnings.append(f"evidence file too large to hash: {rel}")
        if is_entry_candidate(rel):
            entry_candidates.append(rel)

    snapshot = {
        "captured_at": now_iso(),
        "git": git,
        "inventory": inventory,
        "inventory_digest": json_digest(inventory),
        "evidence_hashes": evidence_hashes,
        "evidence_files": sorted(evidence_files),
        "entry_candidates": sorted(entry_candidates),
        "top_directories": sorted(top_directories),
        "sensitive_paths": sorted(set(sensitive_paths)),
        "lockfiles": sorted(lockfiles),
        "symlinks": sorted(set(symlinks)),
        "warnings": warnings,
    }
    return snapshot


def load_state(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"corrupt: {exc}"
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
        return None, "incompatible schema"
    return value, None


def changed_inventory(previous: dict[str, Any], current: dict[str, Any]) -> list[str]:
    paths = set(previous) | set(current)
    return sorted(path for path in paths if previous.get(path) != current.get(path))


def parse_status_paths(lines: Iterable[str], root: Path, top: Path) -> set[str]:
    changed: set[str] = set()
    for line in lines:
        rel = status_path(line, root, top)
        if rel is not None:
            changed.add(rel)
    return changed


def git_changed_paths(root: Path, old_head: str, current_git: dict[str, Any]) -> tuple[set[str], str | None]:
    top = Path(current_git["top"])
    changed = parse_status_paths(current_git.get("status", []), root, top)
    if not old_head or not current_git.get("head") or old_head == current_git.get("head"):
        return changed, None
    result = run_git(root, ["diff", "--name-only", f"{old_head}..{current_git['head']}", "--", "."])
    if result.returncode != 0:
        return changed, "could not compare recorded Git HEAD; used inventory fallback"
    for raw in result.stdout.splitlines():
        candidate = (top / raw).resolve()
        if is_relative_to(candidate, root):
            changed.add(relative_posix(candidate, root))
    return changed, None


def scan_command(args: argparse.Namespace) -> dict[str, Any]:
    root = resolve_root(args.root)
    guide = resolve_inside(root, args.guide, "guide path")
    state_path = resolve_inside(root, args.state, "state path")
    excluded = {relative_posix(guide, root), relative_posix(state_path, root)}
    state, state_error = load_state(state_path)
    guide_exists = guide.is_file()
    current_guide_hash = sha256_file(guide) if guide_exists else None

    if guide_exists and state is None:
        return {
            "schema_version": SCHEMA_VERSION,
            "root": str(root),
            "mode": "blocked_manual_edit",
            "has_changes": None,
            "guide_path": str(guide),
            "state_path": str(state_path),
            "guide_matches_state": False,
            "blocked_reason": f"existing guide cannot be verified because state is {state_error}",
        }
    if guide_exists and state and state.get("guide_sha256") != current_guide_hash:
        return {
            "schema_version": SCHEMA_VERSION,
            "root": str(root),
            "mode": "blocked_manual_edit",
            "has_changes": None,
            "guide_path": str(guide),
            "state_path": str(state_path),
            "guide_matches_state": False,
            "blocked_reason": "WORKSPACE_GUIDE.md differs from the recorded guide hash",
        }

    snapshot = collect_snapshot(root, excluded)
    mode = "full"
    changed: set[str] = set()
    compare_warning: str | None = None
    previous_evidence_set: set[str] = set()
    baseline_usable = bool(
        state is not None
        and guide_exists
        and state.get("root") == str(root)
    )
    if baseline_usable and state is not None:
        mode = "incremental"
        prior_snapshot = state.get("snapshot", {})
        changed.update(
            changed_inventory(prior_snapshot.get("inventory", {}), snapshot["inventory"])
        )
        previous_git = prior_snapshot.get("git")
        current_git = snapshot.get("git")
        if previous_git and current_git:
            git_changed, compare_warning = git_changed_paths(
                root, previous_git.get("head"), current_git
            )
            changed.update(git_changed)
        elif bool(previous_git) != bool(current_git):
            changed.update(snapshot["inventory"].keys())
        previous_evidence = prior_snapshot.get("evidence_hashes", {})
        previous_evidence_set = set(previous_evidence)
        current_evidence = snapshot.get("evidence_hashes", {})
        changed.update(
            path
            for path in set(previous_evidence) | set(current_evidence)
            if previous_evidence.get(path) != current_evidence.get(path)
        )

    warnings = list(snapshot["warnings"])
    if compare_warning:
        warnings.append(compare_warning)
    evidence_set = set(snapshot["evidence_files"]) | previous_evidence_set
    changed_evidence = sorted(path for path in changed if path in evidence_set)
    result = {
        "schema_version": SCHEMA_VERSION,
        "root": str(root),
        "mode": mode,
        "has_changes": True if mode == "full" else bool(changed),
        "captured_at": snapshot["captured_at"],
        "guide_path": str(guide),
        "state_path": str(state_path),
        "guide_matches_state": not guide_exists or bool(state),
        "previous_generated_at": state.get("generated_at") if state else None,
        "git": snapshot["git"],
        "inventory_count": len(snapshot["inventory"]),
        "inventory_digest": snapshot["inventory_digest"],
        "changed_paths": sorted(changed),
        "changed_evidence": changed_evidence,
        "evidence_files": snapshot["evidence_files"],
        "entry_candidates": snapshot["entry_candidates"],
        "top_directories": snapshot["top_directories"],
        "sensitive_paths": snapshot["sensitive_paths"],
        "lockfiles": snapshot["lockfiles"],
        "symlinks": snapshot["symlinks"],
        "warnings": warnings,
    }
    return result


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_name = handle.name
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def record_command(args: argparse.Namespace) -> dict[str, Any]:
    root = resolve_root(args.root)
    guide = resolve_inside(root, args.guide, "guide path")
    state_path = resolve_inside(root, args.state, "state path")
    excluded = {relative_posix(guide, root), relative_posix(state_path, root)}
    if not guide.is_file():
        raise SnapshotError(f"guide does not exist: {guide}")
    try:
        text = guide.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise SnapshotError(f"guide must be readable UTF-8 text: {exc}") from exc
    line_count = len(text.splitlines())
    if line_count > args.max_lines:
        raise SnapshotError(f"guide has {line_count} lines; maximum is {args.max_lines}")
    required_headings = [
        "## 摘要",
        "## 目前狀態",
        "## 專案入口",
        "## 主要目錄",
        "## 安裝與啟動",
        "## 檢查方法與實測結果",
        "## 修改護欄",
        "## 待確認",
    ]
    actual_headings = [line.strip() for line in text.splitlines() if line.startswith("## ")]
    if actual_headings != required_headings:
        raise SnapshotError("guide must contain exactly the eight required headings in order")
    snapshot = collect_snapshot(root, excluded)
    state = {
        "schema_version": SCHEMA_VERSION,
        "root": str(root),
        "generated_at": now_iso(),
        "guide_path": relative_posix(guide, root),
        "guide_sha256": sha256_file(guide),
        "snapshot": {
            "captured_at": snapshot["captured_at"],
            "git": snapshot["git"],
            "inventory": snapshot["inventory"],
            "inventory_digest": snapshot["inventory_digest"],
            "evidence_hashes": snapshot["evidence_hashes"],
        },
    }
    atomic_write_json(state_path, state)
    return {
        "schema_version": SCHEMA_VERSION,
        "root": str(root),
        "recorded": True,
        "state_path": str(state_path),
        "guide_sha256": state["guide_sha256"],
        "line_count": line_count,
        "inventory_count": len(snapshot["inventory"]),
        "warnings": snapshot["warnings"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("scan", "record"):
        subparser = subparsers.add_parser(name)
        subparser.add_argument("--root", required=True, help="absolute workspace directory")
        subparser.add_argument("--guide", default=DEFAULT_GUIDE)
        subparser.add_argument("--state", default=DEFAULT_STATE)
        if name == "record":
            subparser.add_argument("--max-lines", type=int, default=80)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = scan_command(args) if args.command == "scan" else record_command(args)
    except (SnapshotError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
