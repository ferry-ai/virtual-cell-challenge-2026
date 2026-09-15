"""Deterministic helpers: ids, hashes, clocks, write-once files, text deltas.

Two habits from the analysis side of this repo are kept here. Identifiers are derived
from content, so re-running the same step lands on the same identity and a duplicate
send is detectable rather than probable; and writes refuse to overwrite, so a failed or
superseded attempt stays readable as what happened that day.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__ = [
    "utc_now", "sha256_text", "sha256_bytes", "short_id", "slugify",
    "write_new", "write_json_new", "append_jsonl", "read_json", "load_document",
    "normalise", "similarity", "unified_diff", "clip",
]

_WHITESPACE = re.compile(r"\s+")
_UNSAFE = re.compile(r"[^a-z0-9]+")


def utc_now() -> str:
    """UTC timestamp, seconds resolution, always suffixed with Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def short_id(*parts: str, length: int = 16) -> str:
    """A content-derived id. Same parts, same id, on any machine and any day."""
    joined = "\x1f".join(str(part) for part in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:length]


def slugify(text: str, *, max_length: int = 48) -> str:
    normalised = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = _UNSAFE.sub("-", normalised.lower()).strip("-")
    return (slug[:max_length].rstrip("-") or "untitled")


def write_new(path: Path | str, data: str | bytes) -> Path:
    """Write a file that must not already exist. Atomic, UTF-8, no overwriting.

    The refusal is the point: probe outputs, prompts and replies are evidence, and a
    re-run goes to a new destination instead of over the old one.
    """
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = data.encode("utf-8") if isinstance(data, str) else data
    temporary = path.with_name(path.name + ".partial")
    temporary.write_bytes(payload)
    os.replace(temporary, path)
    return path


def write_json_new(path: Path | str, obj: Any) -> Path:
    return write_new(path, json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def append_jsonl(path: Path | str, obj: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


def read_json(path: Path | str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_document(path: Path | str) -> dict:
    """Load a .json (standard library) or .yaml/.yml (PyYAML, imported lazily) mapping."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml  # noqa: PLC0415 -- optional: JSON needs nothing installed
        except ModuleNotFoundError as error:  # pragma: no cover - environment dependent
            raise RuntimeError(
                f"{path} is YAML but PyYAML is not installed; install it or use JSON"
            ) from error
        loaded = yaml.safe_load(text)
    else:
        loaded = json.loads(text)
    if not isinstance(loaded, dict):
        raise ValueError(f"{path}: expected a mapping at the top level")
    return loaded


def normalise(text: str) -> str:
    """Case- and whitespace-insensitive form, used only for comparing, never for storing."""
    return _WHITESPACE.sub(" ", text.strip().lower())


def similarity(left: str, right: str) -> float:
    """Ratio in [0, 1] between two texts. Used by the stagnation and convergence tests."""
    if not left and not right:
        return 1.0
    return difflib.SequenceMatcher(None, normalise(left), normalise(right)).ratio()


def unified_diff(before: str, after: str, *, before_label: str, after_label: str) -> str:
    """What changed between two rounds, in a form a person can read."""
    lines = difflib.unified_diff(
        before.splitlines(), after.splitlines(),
        fromfile=before_label, tofile=after_label, lineterm="", n=2,
    )
    return "\n".join(lines)


def clip(text: str, limit: int) -> str:
    """Shorten for display, and say so. Storage always keeps the full text."""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n[... {len(text) - limit} caratteri non mostrati ...]"
