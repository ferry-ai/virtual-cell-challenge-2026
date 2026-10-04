"""Create a separate exporter revision; preserve the failed exporter verbatim."""
from pathlib import Path
here = Path(__file__).resolve().parent
text = (here / "export_effects.py").read_text()
old = '''        if not observed.any(axis=1).all():
            raise ValueError(f"{name}: a target has no observed genes")'''
new = '''        missing = validate_coverage(name, raw, effects["prod"], names)'''
assert text.count(old) == 1
helper = '''
def validate_coverage(name, raw, production, targets):
    """Keep genuine production no-transfer rows, identically masked in both paired arms."""
    missing = ~np.isfinite(raw).any(axis=1)
    if missing.any():
        if name not in ("prod", "prod_wR") or np.isfinite(production[missing]).any():
            raise ValueError(f"{name}: unexpected target with no observed genes")
    return [targets[i] for i in np.flatnonzero(missing)]


'''
text = text.replace('def main():', helper + 'def main():', 1).replace(old, new)
text = text.replace('files[name] = {"sha256":', 'files[name] = {"baseline_only_targets": missing, "sha256":')
with (here / "export_effects_r2.py").open("x", encoding="utf-8") as f:
    f.write(text)
