"""Install the bundled VCC agent skill into a coding agent's skills directory.

The skill ships as package data at ``vcc/skill/`` (see ``src/vcc/skill/``), so it
travels inside the wheel. But agents discover skills from specific on-disk
locations (``~/.claude/skills/``, Gemini's config, an installed plugin) — never
from Python site-packages. ``vcc skill install`` is the small copy step that moves
the bundled skill from the installed package into the location the agent scans.

Dependency-free and fast (only stdlib + importlib.resources) — no heavy imports,
so ``vcc skill install`` stays as cheap as ``vcc version``.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

from vcc import __version__

SKILL_DIR_NAME = "vcc"  # the folder + SKILL.md `name:` the agent sees
MARKER = ".vcc-skill-version"  # sentinel so we know a dir is ours (safe to overwrite/remove)
AGENTS = ("claude", "codex", "gemini")


class SkillInstallError(Exception):
    """A user-facing problem installing the bundled skill."""


@dataclass
class InstallResult:
    agent: str
    path: str
    status: str  # installed | updated | already current | removed | error
    version: str = field(default=__version__)
    error: str | None = None

    def to_dict(self) -> dict:
        d: dict = {"agent": self.agent, "path": self.path, "status": self.status, "version": self.version}
        if self.error:
            d["error"] = self.error
        return d


def agent_target(agent: str) -> Path:
    """Resolve the skills directory for a given agent, honoring config-dir env vars."""
    home = Path.home()
    if agent == "claude":
        base = Path(os.environ.get("CLAUDE_CONFIG_DIR") or (home / ".claude"))
        return base / "skills" / SKILL_DIR_NAME
    if agent == "gemini":
        return home / ".gemini" / "config" / "skills" / SKILL_DIR_NAME
    if agent == "codex":
        # Codex CLI reads personal skills from ~/.codex/skills/ (honoring CODEX_HOME);
        # project skills live in ./.codex/skills/ — pass --dir for that.
        base = Path(os.environ.get("CODEX_HOME") or (home / ".codex"))
        return base / "skills" / SKILL_DIR_NAME
    raise SkillInstallError(f"Unknown agent '{agent}'. Use one of {', '.join(AGENTS)}, or pass --dir.")


def _agent_base(agent: str) -> Path:
    """The agent's config home whose existence signals that agent is present."""
    home = Path.home()
    if agent == "claude":
        return Path(os.environ.get("CLAUDE_CONFIG_DIR") or (home / ".claude"))
    if agent == "gemini":
        return home / ".gemini"
    if agent == "codex":
        return Path(os.environ.get("CODEX_HOME") or (home / ".codex"))
    raise SkillInstallError(f"Unknown agent '{agent}'. Use one of {', '.join(AGENTS)}, or pass --dir.")


def detected_agents() -> list[str]:
    """Agents whose config dir already exists on this machine (in AGENTS order)."""
    return [a for a in AGENTS if _agent_base(a).is_dir()]


def _bundled_skill_dir() -> Path:
    """Locate the bundled skill inside the installed package."""
    src = resources.files("vcc") / "skill"
    if not (src / "SKILL.md").is_file():
        raise SkillInstallError(
            "This build has no bundled skill (vcc/skill/SKILL.md is missing). "
            "Reinstall the CLI from a build that includes it."
        )
    return Path(str(src))


def _resolve_targets(agent: str | None, dir_: str | None) -> list[tuple[str, Path]]:
    if dir_:
        p = Path(dir_).expanduser()
        # If they point at a parent dir, install into a `vcc/` subfolder; if they
        # already named the leaf `vcc`, use it as-is.
        target = p if p.name == SKILL_DIR_NAME else p / SKILL_DIR_NAME
        return [("custom", target)]
    if agent == "all":
        return [(a, agent_target(a)) for a in AGENTS]
    if agent in (None, "auto"):
        # Auto: install for every agent already present on the machine, so we never
        # silently miss the agent the user actually runs — and never clutter agents
        # they don't (no dir created for an absent one). Fall back to Claude on a
        # fresh machine where none is detected yet.
        chosen = detected_agents() or ["claude"]
        return [(a, agent_target(a)) for a in chosen]
    return [(agent, agent_target(agent))]


def _is_ours(target: Path) -> bool:
    return (target / MARKER).is_file()


def _marker_value(target: Path) -> str | None:
    marker = target / MARKER
    if marker.is_file():
        return marker.read_text(encoding="utf-8").strip()
    return None


def _signature(src: Path) -> str:
    """`<version>:<content-hash>` of the bundled skill.

    Keying "already current" on this (not just the version) means a rebuilt skill
    is detected as changed and re-installed even when the version string hasn't
    moved — the common case for pre-release builds that all share one version.
    """
    h = hashlib.sha256()
    for f in sorted(p for p in src.rglob("*") if p.is_file()):
        h.update(f.relative_to(src).as_posix().encode("utf-8") + b"\0")
        h.update(f.read_bytes() + b"\0")
    return f"{__version__}:{h.hexdigest()[:16]}"


def _remove(path: Path) -> None:
    """Remove a file, symlink, or directory (symlink-safe — never rmtree a link)."""
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _install_one(name: str, target: Path, src: Path, sig: str, force: bool) -> InstallResult:
    # exists() follows symlinks, so a dangling link reports False — check the link too,
    # otherwise mkdir later raises FileExistsError on the broken symlink.
    existed = target.exists() or target.is_symlink()
    is_empty_dir = target.is_dir() and not target.is_symlink() and not any(target.iterdir())
    if existed and not is_empty_dir and not _is_ours(target) and not force:
        raise SkillInstallError(
            f"{target} already exists and wasn't created by vcc. "
            "Re-run with --force to overwrite, or choose another --dir."
        )
    # Skip only when nothing changed (marker matches the current signature and the
    # skill is actually present) — and never skip under --force.
    if not force and existed and _marker_value(target) == sig and (target / "SKILL.md").is_file():
        return InstallResult(name, str(target), "already current")

    # Stage into a temp dir on the same filesystem (marker included), then swap it in.
    # The existing install is moved *aside* (a fast rename) rather than deleted before
    # the swap, and restored if anything fails — so a crash/failed replace never leaves
    # the user with no skill or a marker-less partial dir that blocks reinstall.
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.parent / f".{target.name}.vcc-staging"
    backup = target.parent / f".{target.name}.vcc-old"
    _remove(staging)  # clear leftovers from a prior interrupted run
    _remove(backup)
    try:
        shutil.copytree(src, staging)
        (staging / MARKER).write_text(sig + "\n", encoding="utf-8")
        if existed:
            os.replace(target, backup)  # move the old install aside (atomic, fast)
        try:
            os.replace(staging, target)  # swap the new one in
        except OSError:
            if existed and not target.exists():
                os.replace(backup, target)  # restore the old install on failure
            raise
    finally:
        _remove(staging)  # no-op once the replace succeeded
        _remove(backup)   # no-op if it was restored
    return InstallResult(name, str(target), "updated" if existed else "installed")


def install(*, agent: str | None = None, dir_: str | None = None, force: bool = False) -> list[InstallResult]:
    """Copy the bundled skill into the resolved target dir(s).

    Refuses to clobber a directory we didn't create unless ``force`` is set. Skips
    (reports "already current") only when the installed content matches. With
    ``--agent all``, a per-target failure is captured as an ``error`` result rather
    than aborting the loop, so successes are never silently discarded.
    """
    try:
        src = _bundled_skill_dir()  # raises SkillInstallError if SKILL.md is absent
        sig = _signature(src)       # reads every bundled file — may raise OSError
    except OSError as exc:
        raise SkillInstallError(f"Could not read the bundled skill: {exc}") from exc
    results: list[InstallResult] = []
    for name, target in _resolve_targets(agent, dir_):
        try:
            results.append(_install_one(name, target, src, sig, force))
        except (SkillInstallError, OSError) as exc:
            results.append(InstallResult(name, str(target), "error", error=str(exc)))
    return results


def uninstall(*, agent: str | None = None, dir_: str | None = None) -> list[InstallResult]:
    """Remove skill directories that carry our marker. Never touches foreign dirs."""
    results: list[InstallResult] = []
    for name, target in _resolve_targets(agent, dir_):
        if (target.exists() or target.is_symlink()) and _is_ours(target):
            try:
                _remove(target)  # symlink-safe (rmtree on a symlink would raise)
                results.append(InstallResult(name, str(target), "removed"))
            except OSError as exc:
                results.append(InstallResult(name, str(target), "error", error=str(exc)))
    return results
