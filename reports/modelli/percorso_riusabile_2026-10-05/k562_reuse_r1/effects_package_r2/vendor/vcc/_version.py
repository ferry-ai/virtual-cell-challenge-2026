"""Version resolution for the vcc CLI.

Kept dependency-free and cheap to import so it does not slow ``vcc --version``
or ``vcc --help`` (requirement D6: cold start under 500 ms).
"""

from __future__ import annotations

import platform
from importlib import metadata

from vcc import __version__


def vcc_version() -> str:
    """Return the installed vcc version.

    Prefer the installed distribution metadata (authoritative once the package
    is installed) and fall back to the in-source ``__version__`` when running
    from a source tree that was never installed.
    """
    # "vcc-cli" is the DISTRIBUTION name (pyproject `[project].name`), which is
    # what importlib.metadata keys on — not the import package, which is `vcc`.
    # Querying "vcc" here would always raise and silently fall through to the
    # in-source constant, defeating the point of asking the installed metadata.
    try:
        return metadata.version("vcc-cli")
    except metadata.PackageNotFoundError:
        return __version__


def version_info() -> dict[str, str]:
    """Structured version data for both human and ``--json`` output.

    Includes the build channel and the endpoint that channel implies — the two
    facts a support ticket needs to explain "why is it talking to that host?".
    """
    from vcc.config import PROD_ENDPOINT, channel, endpoint_is_locked

    return {
        "vcc": vcc_version(),
        "python": platform.python_version(),
        "platform": platform.platform(terse=True),
        "channel": channel(),
        "endpoint": PROD_ENDPOINT if endpoint_is_locked() else "configurable (dev build)",
    }
