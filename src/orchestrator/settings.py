"""The orchestrator's own configuration: services, roles, routes, limits, guards.

Everything that decides behaviour is here and comes from a file the operator edits. The
engine reads this; it never reads behaviour out of a reply. Two settings are guards
rather than knobs:

* `execution.model_code` may be `quarantine` or `review_only`. The value `run` is
  rejected by the loader: in this version code produced by a model is an artefact to be
  read, and running it needs a separate mechanism that does not exist yet.
* `outbound.allowed_roots` lists the only directories a brief may attach material from,
  on top of the brief's own directory. It starts empty, so no project file leaves the
  machine by accident.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .convergence import Limits
from .util import load_document

STAGES = ("frame", "solve", "checkpoint", "review")
EXECUTION_POLICIES = ("quarantine", "review_only")
PLAN_APPROVAL = ("required", "auto")


class ConfigError(ValueError):
    """The configuration is inconsistent. Raised at load time, never mid-run."""


def _family(services: dict[str, Any], service: str) -> str:
    """Which model sits behind a service name. Defaults to the name itself."""
    return str((services.get(service) or {}).get("family") or service)


@dataclass(frozen=True)
class Route:
    name: str
    stages: dict[str, tuple[str, ...]]     # stage -> roles taking part
    stand_in: dict[str, str] = field(default_factory=dict)   # solve role -> reserve service

    def roles(self, stage: str) -> tuple[str, ...]:
        return self.stages.get(stage, ())

    def reserve_for(self, role: str) -> str | None:
        """Which service may take this seat when its usual holder does not answer.

        Declared in the route, before the run, never decided while one is going. A seat
        with no reserve behaves as it always did: the absence is visible and, past the
        tolerance, it stops the run.
        """
        return self.stand_in.get(role)

    @property
    def has_solve(self) -> bool:
        return bool(self.stages.get("solve"))


@dataclass(frozen=True)
class Settings:
    path: Path
    config_dir: Path
    services: dict[str, dict[str, Any]]
    roles: dict[str, str]
    routes: dict[str, Route]
    default_route: str
    limits: Limits
    allowed_roots: tuple[Path, ...]
    execution_policy: str
    plan_approval: str
    checkpoint_every: int
    state_root_override: str | None
    raw: dict[str, Any] = field(repr=False, default_factory=dict)

    # ----------------------------------------------------------------- accessors
    def route(self, name: str) -> Route:
        if name not in self.routes:
            raise ConfigError(
                f"unknown route {name!r}; configured routes: {', '.join(sorted(self.routes))}")
        return self.routes[name]

    def route_or_default(self, name: str | None) -> Route:
        """Resolve a route name against the allowlist. A hint from a reply lands here."""
        if not name or name not in self.routes:
            return self.route(self.default_route)
        return self.route(name)

    def service_of(self, role: str) -> str:
        if role not in self.roles:
            raise ConfigError(f"role {role!r} is not mapped to a service")
        return self.roles[role]

    def service_config(self, service: str) -> dict[str, Any]:
        if service not in self.services:
            raise ConfigError(f"service {service!r} is not configured")
        return self.services[service]

    def family(self, service: str) -> str:
        """Which model is behind a service. Two sessions of one model share a family.

        Only useful because a reserve session is a second instance of the peer's model:
        when it sits in, the round is one model talking to itself, and agreement in that
        round has to be reported as such.
        """
        return _family(self.services, service)

    @property
    def route_names(self) -> tuple[str, ...]:
        return tuple(sorted(self.routes))


def load_settings(path: Path | str) -> Settings:
    path = Path(path).resolve()
    document = load_document(path)

    services = document.get("services") or {}
    if not isinstance(services, dict) or not services:
        raise ConfigError(f"{path}: 'services' must be a non-empty mapping")
    roles = document.get("roles") or {}
    if not isinstance(roles, dict) or not roles:
        raise ConfigError(f"{path}: 'roles' must be a non-empty mapping")
    for role, service in roles.items():
        if service not in services:
            raise ConfigError(f"{path}: role {role!r} points at unknown service {service!r}")

    raw_routes = document.get("routes") or {}
    if not isinstance(raw_routes, dict) or not raw_routes:
        raise ConfigError(f"{path}: 'routes' must be a non-empty mapping")
    routes: dict[str, Route] = {}
    for name, stages in raw_routes.items():
        if not isinstance(stages, dict):
            raise ConfigError(f"{path}: route {name!r} must map stages to role lists")
        stages = dict(stages)
        reserves = stages.pop("stand_in", None) or {}
        if not isinstance(reserves, dict):
            raise ConfigError(f"{path}: route {name!r}: 'stand_in' must map a solve role to "
                              f"the service that replaces it")
        resolved: dict[str, tuple[str, ...]] = {}
        for stage, members in stages.items():
            if stage not in STAGES:
                raise ConfigError(f"{path}: route {name!r} has unknown stage {stage!r}; "
                                  f"stages are {STAGES}")
            members = [members] if isinstance(members, str) else list(members or [])
            unknown = [role for role in members if role not in roles]
            if unknown:
                raise ConfigError(f"{path}: route {name!r} stage {stage!r} names unmapped "
                                  f"roles {unknown}")
            resolved[stage] = tuple(members)
        if not resolved.get("solve"):
            raise ConfigError(f"{path}: route {name!r} has no 'solve' stage; a route that "
                              f"solves nothing cannot produce a result")
        for role, reserve in reserves.items():
            if role not in resolved["solve"]:
                raise ConfigError(f"{path}: route {name!r} declares a stand-in for {role!r}, "
                                  f"which does not solve in this route")
            if reserve not in services:
                raise ConfigError(f"{path}: route {name!r}: stand-in for {role!r} names "
                                  f"unknown service {reserve!r}")
            if reserve == roles[role]:
                raise ConfigError(
                    f"{path}: route {name!r}: the stand-in for {role!r} is {reserve!r}, the "
                    f"same service that already holds the seat. A reserve must be a "
                    f"separate session, or it is not a reserve.")
            if _family(services, reserve) == _family(services, roles[role]):
                raise ConfigError(
                    f"{path}: route {name!r}: the stand-in for {role!r} is another session "
                    f"of {_family(services, reserve)!r}, the very model that just failed to "
                    f"answer. A seat is covered by a second session of the service that is "
                    f"still replying, not of the one that is down.")
        routes[name] = Route(name=name, stages=resolved,
                             stand_in={str(role): str(reserve)
                                       for role, reserve in reserves.items()})

    default_route = str(document.get("default_route") or next(iter(routes)))
    if default_route not in routes:
        raise ConfigError(f"{path}: default_route {default_route!r} is not a configured route")

    execution = document.get("execution") or {}
    policy = str(execution.get("model_code", "quarantine"))
    if policy not in EXECUTION_POLICIES:
        raise ConfigError(
            f"{path}: execution.model_code is {policy!r}. Allowed: {EXECUTION_POLICIES}. "
            f"Running code produced by a model needs a separate, explicitly configured "
            f"mechanism, which this version does not provide.")

    plan_approval = str((document.get("planning") or {}).get("approval", "required"))
    if plan_approval not in PLAN_APPROVAL:
        raise ConfigError(f"{path}: planning.approval must be one of {PLAN_APPROVAL}")

    outbound = document.get("outbound") or {}
    allowed_roots = tuple(
        Path(entry).expanduser().resolve() for entry in (outbound.get("allowed_roots") or [])
    )

    return Settings(
        path=path,
        config_dir=path.parent,
        services={name: dict(config) for name, config in services.items()},
        roles={str(role): str(service) for role, service in roles.items()},
        routes=routes,
        default_route=default_route,
        limits=Limits.from_config(document.get("limits")),
        allowed_roots=allowed_roots,
        execution_policy=policy,
        plan_approval=plan_approval,
        checkpoint_every=int((document.get("planning") or {}).get("checkpoint_every", 0)),
        state_root_override=document.get("state_root"),
        raw=document,
    )
