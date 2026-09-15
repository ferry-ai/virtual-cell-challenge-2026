"""Adapter construction. One service, one channel, chosen only by configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..util import load_document
from .base import Adapter, Health, Reply, Request, TransportError, TRANSPORT_KINDS
from .gemini_cli import GeminiCliAdapter
from .manual import ManualAdapter
from .scripted import ScriptedAdapter
from .web import WebChatAdapter

__all__ = [
    "Adapter", "Health", "Reply", "Request", "TransportError", "TRANSPORT_KINDS",
    "GeminiCliAdapter", "ManualAdapter", "ScriptedAdapter", "WebChatAdapter",
    "build_adapter", "ADAPTERS",
]

ADAPTERS = {
    "gemini_cli": GeminiCliAdapter,
    "manual": ManualAdapter,
    "scripted": ScriptedAdapter,
    "web": WebChatAdapter,
}


def build_adapter(service: str, service_config: dict[str, Any], *, state_root: Path,
                  config_dir: Path) -> Adapter:
    """Instantiate the adapter a service declares. Unknown kinds fail loudly."""
    kind = str(service_config.get("adapter", ""))
    if kind not in ADAPTERS:
        raise ValueError(
            f"service {service!r} declares adapter {kind!r}; known adapters: "
            f"{', '.join(sorted(ADAPTERS))}")
    settings = dict(service_config)
    if kind == "scripted" and settings.get("script_dir"):
        # Relative to the configuration file, so a run does not depend on the shell's cwd.
        script_dir = Path(settings["script_dir"])
        if not script_dir.is_absolute():
            script_dir = config_dir / script_dir
        settings["script_dir"] = str(script_dir)
    if kind == "web":
        profile_name = str(settings.get("profile", service))
        profile_path = config_dir / "services" / f"{profile_name}.yaml"
        if not profile_path.exists():
            alternative = profile_path.with_suffix(".json")
            if not alternative.exists():
                raise FileNotFoundError(
                    f"service {service!r} needs a profile at {profile_path} (or .json)")
            profile_path = alternative
        settings["profile_data"] = load_document(profile_path)
        settings["profile_path"] = str(profile_path)
        # `profile` is the selector map (which page, which boxes); `profile_dir` is the
        # browser session (which login). A reserve service reuses the first and needs its
        # own second: Chrome refuses to open one profile directory twice, and two logins
        # in one directory would not be two sessions anyway.
        session_dir = str(settings.get("profile_dir") or profile_name)
        settings.setdefault("user_data_dir", str(state_root / "profiles" / session_dir))
    return ADAPTERS[kind](service, settings)
