"""Execute one frozen NTC plan on cloud CPU; never launch or transfer anything."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import time
import numpy as np
import scipy.sparse as sp
import ntc_cells as reader


def available_memory():
    if os.name=='nt':
        import ctypes
        class MemoryStatus(ctypes.Structure):
            _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),
                      ('total',ctypes.c_ulonglong),('available',ctypes.c_ulonglong),
                      ('total_page',ctypes.c_ulonglong),('avail_page',ctypes.c_ulonglong),
                      ('total_virtual',ctypes.c_ulonglong),('avail_virtual',ctypes.c_ulonglong),
                      ('reserved',ctypes.c_ulonglong)]
        status=MemoryStatus();status.length=ctypes.sizeof(status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise OSError('cannot measure available memory')
        return status.available
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'):
            return int(line.split()[1])*1024
    raise OSError('cannot measure available memory')


def run(plan_path, plan_sha256, locations_path, rows_path, out):
    plan_path, out = Path(plan_path), Path(out)
    if reader.sha(plan_path) != plan_sha256:
        raise ValueError('extraction plan changed')
    if out.exists():
        raise FileExistsError(out)
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    if 'genes' not in plan:
        genes_path=plan_path.parent/plan['genes_file']
        if reader.sha(genes_path)!=plan['genes_sha256']:
            raise ValueError('frozen gene axis changed')
        plan['genes']=json.loads(genes_path.read_text())
    locations = json.loads(Path(locations_path).read_text(encoding='utf-8'))
    if set(locations) != {s['sha256'] for s in plan['sources']}:
        raise ValueError('runtime locations must cover exactly the frozen raw source hashes')
    actual_sizes = {digest:Path(path).stat().st_size for digest,path in locations.items()}
    disk_root = out.parent
    while not disk_root.exists():
        disk_root = disk_root.parent
    resources = dict(cpu_count=os.cpu_count(), available_RAM=available_memory(),
                     disk_free=shutil.disk_usage(disk_root).free, raw_bytes=sum(actual_sizes.values()))
    if resources['available_RAM'] < 1<<30 or resources['disk_free'] < 1<<30:
        raise RuntimeError('NTC extraction needs 1 GiB free RAM and disk at minimum')
    started=time.monotonic()
    selected=reader.selection(plan, locations, rows_path)
    for record in selected:record['part_id']=plan['part_id']
    # Counts remain sparse; only model batches will be densified.
    bundle=reader.extract(plan, locations, selected)
    out.mkdir(parents=True, exist_ok=False)
    sp.save_npz(out/'counts.npz',bundle['counts'])
    np.savez_compressed(out/'axes_depth_mask.npz', genes=np.asarray(plan['genes']),
        native_depth=bundle['native_depth'], masks=bundle['masks'],mask_index=bundle['mask_index'])
    (out/'cells.json').write_text(json.dumps(selected,ensure_ascii=False),encoding='utf-8')
    files={p.name:dict(bytes=p.stat().st_size,sha256=reader.sha(p)) for p in out.iterdir()}
    context_counts=dict(Counter(r['context_id'] for r in selected))
    expected={r['context_id'] for r in plan['controls']}
    if set(context_counts)!=expected:
        raise ValueError('extracted context coverage differs')
    receipt=dict(schema='native-NTC-extraction-completion/1',status='COMPLETE',
        utc=datetime.now(timezone.utc).isoformat(),part_id=plan['part_id'],
        plan_sha256=plan_sha256,files=files,contexts=context_counts,
        native_depth='ingestion obs/depth_native; no denominator computed on aligned genes',
        arrays_shape=list(bundle['counts'].shape),source_files_verified=len(locations),
        raw_sizes_measured=actual_sizes,resources=resources,seconds=time.monotonic()-started,
        NTC_cells_read=len(selected),perturbed_RNA_rows_read=0,
        mean_ablation='mean of the SAME per-cell log1p(CP10k_native) vectors passed to cells encoder',
        normalized_scale='log1p(counts * 10000 / native_depth)',
        storage_parts_need_global_reservoir_merge=True,
        cells_consumed_by_trainer=0,complete_D053=False,
        code={Path(__file__).name:reader.sha(__file__), 'ntc_cells.py':reader.sha(reader.__file__)})
    (out/'complete.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    for name in ('plan','plan-sha256','locations','rows','out'):p.add_argument('--'+name,required=True)
    a=p.parse_args()
    result=run(a.plan,a.plan_sha256,a.locations,a.rows,a.out)
    print(json.dumps({k:result[k] for k in ('status','part_id','contexts','NTC_cells_read','seconds')}))
