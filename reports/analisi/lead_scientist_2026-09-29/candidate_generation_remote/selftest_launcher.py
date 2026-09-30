"""Lightweight launch-gate checks; never touches remote data or runs stages."""
import copy
from pathlib import Path
import tempfile
from generate_candidate import check_confirmation, safe_child


def main():
    valid = {"truth": "full", "comparisons": [{"amplitude": 1.5, "phi_scale": 0.5,
              "generator": "pooled", "passes_confirmation": True, "delta_projection": 0.006,
              "per_seed_delta": [0.005, 0.006, 0.007], "paired_target_bootstrap_interval": [0.001, 0.012]}]}
    assert check_confirmation(valid, 0.5)["phi_scale"] == 0.5
    invalid = []
    for key, value in [("passes_confirmation", False), ("delta_projection", 0.004),
                       ("per_seed_delta", [0.01, -0.001, 0.01]), ("per_seed_delta", [0.01]),
                       ("paired_target_bootstrap_interval", [-0.001, 0.01]),
                       ("amplitude", 1.0), ("generator", "bins")]:
        case = copy.deepcopy(valid)
        case["comparisons"][0][key] = value
        invalid.append(case)
    for case in invalid:
        try:
            check_confirmation(case, 0.5)
        except ValueError:
            pass
        else:
            raise AssertionError(case)
    try:
        check_confirmation(valid, 1.0)
    except ValueError:
        pass
    else:
        raise AssertionError("An unconfirmed dispersion was accepted")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        assert safe_child(root, "data/controls") == root / "data/controls"
        try:
            safe_child(root, "../outside")
        except ValueError:
            pass
        else:
            raise AssertionError("An escaping path was accepted")
    print("PASS: confirmed candidate accepted; eight non-confirmed cases and escaping path rejected")


if __name__ == "__main__":
    main()
