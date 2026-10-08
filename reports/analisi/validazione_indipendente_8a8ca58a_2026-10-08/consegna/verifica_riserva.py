"""Verify the reserve of the delivery: the t36 package that was scored, and what it was made from.

Recomputes the sha256 of the local prediction.vcc in bounded memory and compares it with the checksum
registered before the upload, with the recorded local product and with the size the server received; then
ties the package to its recipe and effects through the receipts. Nothing is uploaded or generated.

    py verifica_riserva.py <out.json>
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
TRIAL = REPO / "reports/invii/trial_2026-10-06"
PRED = REPO / "reports/invii/prediction_t36_2026-10-06"


def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main() -> None:
    out = Path(sys.argv[1])
    local = read(TRIAL / "t36_local_product.json")
    prediction = read(PRED / "prediction.json")
    comparison = read(PRED / "comparison.json")
    receipt = read(TRIAL / "submit_t36_public_receipt.json")
    generation = read(TRIAL / "t36_generation_manifest.json")
    recipe = TRIAL / "t36_recipe_extbank.json"
    path = Path(local["path"])
    h, n = hashlib.sha256(), 0
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(16 << 20), b""):
            h.update(block)
            n += len(block)
    got = h.hexdigest()
    checks = {
        "file_exists": path.is_file(),
        "bytes_equal_recorded": n == local["bytes"] == generation["bytes"] == receipt["bytes_uploaded"],
        "sha256_equals_registered_candidate": got == prediction["candidate_sha256"],
        "sha256_equals_local_product_record": got == local["sha256"],
        "sha256_equals_generation_manifest": got == generation["sha256"],
        "recipe_sha256_of_prediction_equals_generation": prediction["recipe_sha256"] == generation["recipe_sha256"],
        "recipe_file_sha256_lf_equals_registered": hashlib.sha256(
            recipe.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == prediction["recipe_sha256"],
        "entry_of_receipt_equals_scored_entry": receipt["entry_id"] == comparison["entry_id"],
        "official_status_published": comparison["official_status"] == "published",
        "six_published_members_average_to_the_score": abs(
            sum(comparison["scaled_published"]["t36"].values()) / 6 - comparison["score_avg"]) < 1e-12,
    }
    doc = {"utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "what": "reserve of the delivery: t36",
           "package": {"path": str(path), "bytes": n, "sha256": got}, "entry_id": receipt["entry_id"],
           "official_score": comparison["score_avg"], "official_members_scaled": comparison["scaled_published"]["t36"],
           "recipe_sha256": prediction["recipe_sha256"], "emission": prediction["emission"],
           "voted_sources": generation["voted_sources"], "checks": checks, "all_true": all(checks.values()),
           "limits": comparison["limits"]}
    with out.open("x", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    print(json.dumps({"all_true": doc["all_true"], "checks": checks, "sha256": got}, indent=1))


if __name__ == "__main__":
    main()
