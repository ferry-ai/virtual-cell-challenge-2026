"""K562 retry with the same data and rules; only legitimate production no-transfer rows are admitted."""
import io
import sys
import zipfile
import kaggle_bench_v2 as B

original_configure, original_main = B.configure, B.KH.main

def configure(contract=None):
    original_configure(contract)
    B.KH.KERNEL = B.KH.KERNEL.replace('/export_effects.py', '/export_effects_r2.py')
    original_snapshot = B.KH.snapshot
    def snapshot():
        _, names = original_snapshot()
        names += [f"{B.ME}/export_effects_r2.py", f"{B.ME}/EMENDAMENTO_K562.md"]
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for name in names:
                z.writestr(name, (B.REPO / name).read_bytes())
        return buf.getvalue(), names
    B.KH.snapshot = snapshot

def main():
    idx = sys.argv.index('--slug') + 1
    assert sys.argv[idx] == 'rcell-benchv2-k562-t28-r1'
    sys.argv[idx] = 'rcell-benchv2-k562-t28-r2'
    original_main()

B.configure, B.KH.main = configure, main
if __name__ == '__main__':
    if '--launch' in sys.argv:
        raise SystemExit('prepare only; push the prepared r2 with push_prepared.py')
    B.main()
