"""Standard-library guard for a receipt from the one-shot AB selection."""
import hashlib
import json
import math

AB_SHA = "181d7a00b1f5957948e2daf9fcd1f66fae9adb35dbf78aab59a5b2c006133506"


def validate(selection, comparisons, comparison_hashes, selector_sha256):
    if (selection.get("status") != "selection_complete" or selection.get("ab_protocol_sha256") != AB_SHA
            or selection.get("selector_sha256") != selector_sha256
            or set(selection.get("candidates", {})) != {"A", "B"}
            or set(comparisons) != {"A", "B"} or set(comparison_hashes) != {"A", "B"}):
        raise ValueError("Incomplete or unreviewed AB selection receipt")
    checks = selection.get("checks", {})
    for key in ("four_arm_eligibility_identical", "transfer_metric_values_exact", "controls_exact_common_bundle",
                "transfer_counts_axes_exact", "scoring_environment_identical", "selection_uses_original_float64"):
        if checks.get(key) is not True:
            raise ValueError("AB identity/eligibility check missing: " + key)
    eligible = []
    for variant in ("A", "B"):
        comparison, row = comparisons[variant], selection["candidates"][variant]
        d, p = comparison["delta_projection"], comparison["delta_pds_raw"]
        if not math.isfinite(d) or not math.isfinite(p):
            raise ValueError("Non-finite AB comparison")
        valid = bool(d > 0 and p >= 0)
        if (comparison.get("proceed_to_distinct_confirmation") is not valid
                or row.get("eligible") is not valid or row.get("delta_projection") != d or row.get("delta_pds_raw") != p
                or row.get("comparison_sha256") != comparison_hashes[variant]
                or selection["input_files"][variant + "/pilot_comparison.json"]["sha256"] != comparison_hashes[variant]):
            raise ValueError("AB comparison, hash or eligibility differs from selection")
        if valid:
            eligible.append(variant)
    chosen = None if not eligible else eligible[0]
    if len(eligible) == 2:
        chosen = "B" if comparisons["B"]["delta_projection"] > comparisons["A"]["delta_projection"] else "A"
    if selection.get("selected_variant") != chosen:
        raise ValueError("AB selected variant differs from exact prospective rule")
    return chosen


def validate_embedded(review):
    blobs = review["ab_comparison_json"]
    hashes = {v: hashlib.sha256(blobs[v].encode()).hexdigest() for v in ("A", "B")}
    selection_text = review["ab_selection_json"]
    if hashlib.sha256(selection_text.encode()).hexdigest() != review["ab_selection_sha256"]:
        raise ValueError("Embedded AB selection changed")
    chosen = validate(json.loads(selection_text), {v: json.loads(blobs[v]) for v in blobs},
                      hashes, review["ab_selector_sha256"])
    if chosen is None or chosen != review["selected_variant"]:
        raise ValueError("No eligible selected candidate for confirmation")
    return chosen
