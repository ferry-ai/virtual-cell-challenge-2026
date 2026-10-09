"""Disk-backed exact NTC reservoir merge and bounded native normalization.

Campaign failure does not invalidate independently complete, pinned parts. Each
part retains its producer code pins. The merge/normalization reader is separately
pinned. No resampling, downsampling, biological RNA download, or job launch.
"""
from collections import Counter
import gc
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import zipfile

import numpy as np
import scipy.sparse as sp

from ammi_inputs_v3 import checked, read_json, module
from pie_adapter import sha256


def available_memory():
    if os.name == 'nt':
        import ctypes
        class Status(ctypes.Structure):
            _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),
                ('total',ctypes.c_ulonglong),('available',ctypes.c_ulonglong),
                ('total_page',ctypes.c_ulonglong),('available_page',ctypes.c_ulonglong),
                ('total_virtual',ctypes.c_ulonglong),('available_virtual',ctypes.c_ulonglong),
                ('reserved',ctypes.c_ulonglong)]
        value=Status();value.length=ctypes.sizeof(value)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):
            raise OSError('cannot measure free RAM')
        return value.available
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'):return int(line.split()[1])*1024
    raise OSError('cannot measure free RAM')


class DiskControls:
    """One context backed by selected row addresses and read-only sparse mmaps."""
    def __init__(self, context, addresses, bundles, reader, genes):
        self.context = context
        self.addresses = addresses
        self.bundles = bundles
        self.reader = reader
        self.shape = (len(addresses), genes)

    def __len__(self): return self.shape[0]

    def batch(self, start, stop):
        if not 0 <= start < stop <= len(self): raise ValueError('invalid NTC block')
        addresses = self.addresses[start:stop]
        values = np.zeros((len(addresses), self.shape[1]), dtype=np.float32)
        masks = np.zeros(values.shape, dtype=bool)
        for part in sorted(set(addresses[:,0])):
            positions = np.flatnonzero(addresses[:,0] == part)
            rows = addresses[positions,1]
            x, mask = self.reader.normalized_batch(self.bundles[int(part)], rows)
            if not np.isfinite(x).all() or not mask.any(1).all():
                raise ValueError('invalid normalized NTC block')
            values[positions], masks[positions] = x, mask
        return values, masks


def resources_required(parts):
    """Upper bounds from compressed payload headers and pinned metadata sizes."""
    total, peak = 0, 0
    for spec in parts:
        receipt = read_json(spec['completion'])
        root = Path(spec['completion']['path']).parent
        arrays = 0
        for name in ('counts.npz', 'axes_depth_mask.npz'):
            checked(dict(receipt['files'][name], path=str(root/name)))
            with zipfile.ZipFile(root/name) as archive:
                arrays += sum(member.file_size for member in archive.infolist())
        metadata = receipt['files']['cells.json']['bytes']
        # SQLite indices, temporary sorting and sparse staging need extra disk.
        total += arrays + metadata*4
        peak = max(peak, arrays*3 + metadata*8)
    return dict(disk_bytes=total+(1<<30), RAM_bytes=peak+(1<<30))


def validate_origin(spec, receipt):
    policies = {'training': 'ingestion_depth_native',
                'destination': 'full_provided_official_X_before_alignment'}
    role = spec.get('part_role')
    if role not in policies or spec.get('denominator_policy') != policies[role]:
        raise ValueError('NTC role/denominator policy differs')
    # Historical training completions predate these explicit fields; the pinned
    # producer and contract supply them. Official outputs must attest both.
    if role == 'destination' or 'part_role' in receipt or 'denominator_policy' in receipt:
        if receipt.get('part_role') != role or receipt.get('denominator_policy') != policies[role]:
            raise ValueError('NTC completion denominator provenance differs')
    if spec.get('relocation_requires_receipt'):
        restored = read_json(spec['relocation_receipt'])
        files = {f['file']: f for f in restored['files']}
        if restored.get('status') != 'COMPLETE' or restored.get('source_job') != spec['producer_job']:
            raise ValueError('NTC relocation source differs')
        for name, pin in dict(receipt['files'], **{'complete.json': spec['completion']}).items():
            recovered = files.get('ntc/' + receipt['part_id'] + '/' + name, {})
            if any(recovered.get(k) != pin[k] for k in ('bytes', 'sha256')):
                raise ValueError('NTC relocation payload differs')


def stage_controls(parts, genes, expected_contexts, reader_pin, expected_parts, out):
    out = Path(out)
    if out.exists(): raise FileExistsError(out)
    root = out.parent
    while not root.exists(): root = root.parent
    needs = resources_required(parts)
    if shutil.disk_usage(root).free < needs['disk_bytes'] or available_memory() < needs['RAM_bytes']:
        raise RuntimeError('insufficient measured RAM/disk for sparse NTC staging')
    reader = module(reader_pin, 'ammi_streaming_ntc_reader')
    out.mkdir(parents=True)
    database = sqlite3.connect(out/'selection.sqlite')
    database.execute('PRAGMA temp_store=FILE')
    database.execute('PRAGMA cache_size=-32768')
    database.executescript('''
      CREATE TABLE candidates (grp TEXT, context TEXT, priority TEXT, cell TEXT,
        part INTEGER, row INTEGER, UNIQUE(grp,cell));
      CREATE TABLE populations (grp TEXT, part INTEGER, population INTEGER,
        PRIMARY KEY(grp,part));
    ''')
    staged, seen, before = [], set(), Counter()
    for part_number, spec in enumerate(parts):
        receipt = read_json(spec['completion'])
        source = Path(spec['completion']['path']).parent
        part_id = receipt['part_id']
        validate_origin(spec, receipt)
        if (receipt.get('schema') != 'native-NTC-extraction-completion/1'
                or receipt.get('status') != 'COMPLETE' or part_id in seen
                or expected_parts.get(part_id) != spec['plan_sha256']
                or receipt['plan_sha256'] != spec['plan_sha256']
                or receipt['code'] != spec['producer_code']
                or receipt['perturbed_RNA_rows_read'] != 0
                or receipt['normalized_scale'] != 'log1p(counts * 10000 / native_depth)'):
            raise ValueError('NTC part completion/provenance differs')
        seen.add(part_id)
        for name in ('counts.npz', 'axes_depth_mask.npz', 'cells.json'):
            checked(dict(receipt['files'][name], path=str(source/name)))
        counts = sp.load_npz(source/'counts.npz').tocsr()
        with np.load(source/'axes_depth_mask.npz',allow_pickle=False) as raw:
            if raw['genes'].tolist() != list(genes): raise ValueError('NTC gene axis differs')
            bundle = {k:raw[k] for k in ('native_depth','masks','mask_index')}
        depth, masks, index = (bundle[k] for k in ('native_depth','masks','mask_index'))
        records = json.loads((source/'cells.json').read_text(encoding='utf-8'))
        n = len(records)
        if (counts.shape != (n,len(genes)) or list(counts.shape) != receipt['arrays_shape']
                or depth.shape != (n,) or masks.ndim != 2 or masks.shape[1] != len(genes)
                or masks.dtype != bool or index.shape != (n,) or index.dtype.kind not in 'iu'
                or np.any(index < 0) or np.any(index >= len(masks)) or np.any(depth <= 0)
                or not np.isfinite(depth).all() or not np.isfinite(counts.data).all()
                or np.any(counts.data < 0) or not np.equal(counts.data,np.floor(counts.data)).all()):
            raise ValueError('invalid sparse NTC axes or values')
        for start in range(0,n,256):
            stop=min(start+256,n); block=counts[start:stop]
            if np.any(np.asarray(block.sum(1)).ravel() > depth[start:stop]+.5):
                raise ValueError('NTC aligned counts exceed native depth')
            coo=block.tocoo()
            if np.any(~masks[index[start:stop][coo.row],coo.col] & (coo.data!=0)):
                raise ValueError('NTC values outside measured support')
        if dict(Counter(r['context_id'] for r in records)) != receipt['contexts']:
            raise ValueError('NTC context counts differ')
        for row,r in enumerate(records):
            if r['part_id'] != part_id or r['stratum_population'] < 1:
                raise ValueError('NTC part/population differs')
            if len(r['priority']) != 64 or any(c not in '0123456789abcdef' for c in r['priority']):
                raise ValueError('invalid frozen NTC priority')
            group=json.dumps([r['context_id'],[r['identity'][k] for k in reader.BIO],r['stratum']],
                             ensure_ascii=False,separators=(',',':'))
            try:
                database.execute('INSERT INTO candidates VALUES (?,?,?,?,?,?)',
                    (group,r['context_id'],r['priority'],r['cell_key'],part_number,row))
            except sqlite3.IntegrityError as exc:
                raise ValueError('duplicate NTC identity across storage parts') from exc
            population=database.execute('SELECT population FROM populations WHERE grp=? AND part=?',
                                       (group,part_number)).fetchone()
            if population is not None and population[0] != r['stratum_population']:
                raise ValueError('inconsistent NTC part population')
            database.execute('INSERT OR IGNORE INTO populations VALUES (?,?,?)',
                             (group,part_number,r['stratum_population']))
            before[r['context_id']]+=1
        database.commit()
        directory=out/('part_%03d'%part_number);directory.mkdir()
        arrays=dict(bundle,data=counts.data,indices=counts.indices,indptr=counts.indptr)
        for name,value in arrays.items(): np.save(directory/(name+'.npy'),value,allow_pickle=False)
        staged.append(dict(part_id=part_id,number=part_number,shape=list(counts.shape),
            part_role=spec['part_role'],denominator_policy=spec['denominator_policy'],
            completion_sha256=spec['completion']['sha256'],producer_code=receipt['code'],
            plan_sha256=receipt['plan_sha256'],arrays={name:dict(bytes=(directory/(name+'.npy')).stat().st_size,
                sha256=sha256(directory/(name+'.npy'))) for name in arrays}))
        del records,counts,bundle,arrays,depth,masks,index
        gc.collect()
    if seen != set(expected_parts): raise ValueError('NTC storage part coverage differs')
    database.executescript('''
      CREATE INDEX reservoir_order ON candidates(grp,priority,cell);
      CREATE TABLE selected AS SELECT grp,context,priority,cell,part,row FROM
        (SELECT *,row_number() OVER (PARTITION BY grp ORDER BY priority,cell) AS rank FROM candidates)
        WHERE rank<=64;
      CREATE INDEX selected_context ON selected(context,grp,priority,cell);
    ''')
    contexts={r[0] for r in database.execute('SELECT DISTINCT context FROM selected')}
    if contexts != set(expected_contexts): raise ValueError('NTC context coverage differs')
    bundles={}
    for entry in staged:
        i=entry['number'];directory=out/('part_%03d'%i)
        arrays={name:np.load(directory/(name+'.npy'),mmap_mode='r',allow_pickle=False) for name in entry['arrays']}
        counts=sp.csr_matrix((arrays.pop('data'),arrays.pop('indices'),arrays.pop('indptr')),
                            shape=entry['shape'],copy=False)
        bundles[i]=dict(arrays,counts=counts)
    controls,audit={},{}
    for context in sorted(contexts):
        rows=database.execute('SELECT part,row,grp,priority,cell FROM selected WHERE context=? ORDER BY grp,priority,cell',
                              (context,))
        digest=hashlib.sha256();addresses=[]
        for part,row,group,priority,cell in rows:
            addresses.append((part,row))
            digest.update(json.dumps([group,priority,cell,staged[part]['part_id'],row],
                                     ensure_ascii=False,separators=(',',':')).encode()+b'\n')
        addresses=np.asarray(addresses,dtype=np.int64)
        controls[context]=DiskControls(context,addresses,bundles,reader,len(genes))
        audit[context]=dict(cells=len(addresses),cells_before_global_merge=before[context],
                            selection_sha256=digest.hexdigest())
    database.commit();database.close()
    receipt=dict(schema='AMMI-streaming-NTC/4',parts=staged,contexts=audit,
        reader_sha256=reader_pin['sha256'],global_reservoir_cap=64,
        normalization='unchanged pinned reader.normalized_batch',sparse_mmap=True,
        all_dense_control_arrays_materialized=False,complete_D053=False)
    (out/'complete.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    return controls,receipt
