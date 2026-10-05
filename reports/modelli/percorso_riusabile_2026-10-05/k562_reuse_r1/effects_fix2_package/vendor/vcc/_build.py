"""Build-channel marker -- the switch that locks released builds to production.

``CHANNEL`` is ``"dev"`` in the repository, which is what lets developers point the
CLI at localhost or a staging deployment via ``--endpoint`` / ``VCC_ENDPOINT``.

The publish pipeline rewrites this to ``"release"`` immediately before building the
wheel/sdist (see ``scripts/set_channel.py``), so anything installed from PyPI
talks **only** to production and rejects endpoint overrides.

Why a build-time marker and not an env var: an env var could be flipped by
whatever is trying to redirect the CLI, which defeats the purpose. This value is
baked into the artifact. It is a footgun-and-phishing guard, not a hard security
boundary -- someone with write access to their own site-packages can edit it -- but
it means a contestant cannot be talked into "just add
``--endpoint https://not-really-vcc.example``" and hand over their token.
"""

from __future__ import annotations

# Rewritten to "release" by scripts/set_channel.py during publish. Keep the
# literal on one line: the script (and its test) match this exact assignment.
CHANNEL = "release"
