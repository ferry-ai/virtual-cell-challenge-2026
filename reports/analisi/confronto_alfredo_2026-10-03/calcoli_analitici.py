"""Small analytic counterexamples; no data, training or official scoring."""

import json
import math
from pathlib import Path


def responsibility(pi, log_likelihood_gap):
    """Posterior responder weight with fixed prior and component log-likelihoods."""
    odds = pi / (1 - pi) * math.exp(log_likelihood_gap)
    return odds / (1 + odds)


def main():
    result = {
        "kind": "analytic examples, not measurements on cells or official scores",
        "responsibilities": [
            {"pi": pi, "ll1_minus_ll0": gap, "responsibility": responsibility(pi, gap)}
            for pi in (0.01, 0.05, 0.5)
            for gap in (-20, -100)
        ],
        "ordinary_squared_error": [
            {"cosine": c, "optimal_nonnegative_norm_ratio": max(c, 0),
             "minimum_error_ratio": 1 - max(c, 0) ** 2}
            for c in (0, 0.05, 0.12, 0.3)
        ],
        "limitations": [
            "Responder gradient multiplier, not the full parameter gradient or gate gradient.",
            "Squared-error geometry assumes a common fixed support, metric and true control.",
            "The official MSE includes jackknife terms, caps, panel aggregation and anchor scaling.",
        ],
    }
    destination = Path(__file__).with_name("calcoli_analitici.json")
    if destination.exists():
        raise FileExistsError(destination)
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
