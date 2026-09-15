"""Common protocol for comparing transfer, linear, MLP and modular predictors.

The first experiment asks whether a shared response basis plus a small
coefficient head beats a single network, on data that actually exist locally.
It does not assume modularity wins. Proxy metrics in pseudobulk log2FC are
labelled as such; they are not VCC scores.
"""

from .protocol import (  # noqa: F401
    DeltaModel,
    FeatureSpec,
    SplitSpec,
    TrainArrays,
    load_yaml_config,
)
from .universe import GeneUniverse, common_measured_universe  # noqa: F401

__all__ = [
    "DeltaModel",
    "FeatureSpec",
    "SplitSpec",
    "TrainArrays",
    "GeneUniverse",
    "common_measured_universe",
    "load_yaml_config",
]
