"""A local, human-started orchestrator for multi-model research sessions.

The system talks to model services the operator already pays nothing for -- a CLI
authenticated with a Google account, and web interfaces driven in the operator's own
browser session. There are no API keys and no metered endpoints, and there is no
scheduler: every campaign is started by a person typing a command.

Design rules that the code enforces rather than merely documents:

* **Routing, counters, timeouts and stop conditions are deterministic code.** A model
  reply is data. It can populate fields the engine reads from a whitelist; it can never
  change a route, a limit, a permission, or what gets executed (`protocol`, `routing`).
* **Nothing is overwritten.** Raw prompts and raw replies are written once, to a path
  derived from a content hash, the way the analysis scripts write to a fresh `--out`.
* **Agreement is not proof.** `convergence` distinguishes a verified completion from a
  mere convergence of proposals, and the report keeps the distinction in words.
"""

__version__ = "0.1.0"
