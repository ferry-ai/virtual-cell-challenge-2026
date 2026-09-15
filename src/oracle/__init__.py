"""Deterministic numerical oracles.

Independent of the multi-agent orchestrator and of the VCC modelling
code. A verifier in this package recalculates a claim from data; it
does not judge biological hypotheses and it does not call a model.
"""

from .pairwise_loss import VERIFIER_NAME, VERIFIER_VERSION, verify_paths

__version__ = VERIFIER_VERSION
__all__ = ["VERIFIER_NAME", "VERIFIER_VERSION", "verify_paths"]
