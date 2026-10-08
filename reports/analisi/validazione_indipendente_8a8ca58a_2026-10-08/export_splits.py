"""Write one explicit split file per fold of the frozen manifest, in the shape DATI-TRANSFER's
fold_bank.validate_split reads: id, regime, held_groups, hidden_targets, protected_units, group_aliases.

C folds hold a lineage with no hidden target. J folds add the panel symbols of the hidden test group;
for a universe wider than the panel the rule `hidden_group(symbol) == test_group` of the manifest applies
to every symbol and component, and the list written here is only its restriction to the panel.

    py export_splits.py <manifest_fold_v1.json> <new out dir>
"""
import hashlib
import json
import sys
from pathlib import Path


def hidden_group(symbol: str, groups: int = 5) -> int:
    return int(hashlib.sha256(symbol.encode("utf-8")).hexdigest(), 16) % groups


def main() -> None:
    manifest_path, out = Path(sys.argv[1]), Path(sys.argv[2])
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    out.mkdir(parents=True, exist_ok=False)
    aliases = {g: name for name, lin in m["lineages"].items() for g in lin["registry_groups"] if g != name}
    rule = m["hidden_target_rule"]
    test = sorted(m["panel_hidden_groups"][str(rule["test_group"])])
    assert all(hidden_group(t, rule["groups"]) == rule["test_group"] for t in test)
    base = {"manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(), "manifest_version": m["version"],
            "protected_units": ["h1_test"], "group_aliases": aliases,
            "hidden_rule": rule["function"] + " == %d, on every component of every label" % rule["test_group"]}
    written = {}
    for fold in m["folds_C"]:
        for regime, hidden in (("C", []), ("J", test)):
            doc = {"id": fold["id"] if regime == "C" else fold["id"].replace("C-", "J-"), "regime": regime,
                   "held_groups": [fold["lineage"]], "hidden_targets": hidden,
                   "exclude_tables": fold["exclude_tables"], "exclude_units": fold["exclude_units"],
                   "truth": fold["truth"], **base}
            path = out / (doc["id"] + ".json")
            path.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
            written[doc["id"]] = hashlib.sha256(path.read_bytes()).hexdigest()
    doc = {"id": "T-all", "regime": "T", "held_groups": [], "hidden_targets": test, "exclude_tables": [],
           "exclude_units": [], "truth": "per lineage, its own table on the hidden targets", **base}
    (out / "T-all.json").write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    written["T-all"] = hashlib.sha256((out / "T-all.json").read_bytes()).hexdigest()
    (out / "INDEX.json").write_text(json.dumps({"splits": written, **base}, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"written": len(written), "aliases": aliases, "hidden_panel_targets": len(test)}))


if __name__ == "__main__":
    main()
