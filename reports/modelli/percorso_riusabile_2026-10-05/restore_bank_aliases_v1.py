"""Consumer access adapter: restore explicit original names with exact hash checks."""
import json,shutil
from pathlib import Path
from sample_reader import sha


def restore(mounted_root,expected_layout_sha256,out):
    root=Path(mounted_root).resolve();out=Path(out).resolve()
    if out.exists():raise ValueError('new consumer output required')
    if sha(root/'layout.json')!=expected_layout_sha256:raise ValueError('dataset layout changed')
    layout=json.loads((root/'layout.json').read_text())
    for entry in layout['files']:
        source=(root/entry['alias']).resolve();dest=(out/entry['original_path']).resolve()
        if not source.is_relative_to(root) or not dest.is_relative_to(out):raise ValueError('unsafe alias')
        if source.stat().st_size!=entry['bytes'] or sha(source)!=entry['sha256']:raise ValueError('mounted bytes changed')
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
        if sha(dest)!=entry['sha256']:raise ValueError('restored bytes changed')
    return out
