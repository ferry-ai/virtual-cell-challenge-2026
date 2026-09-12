"""Bounded Parquet column projection; no full atlas download."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.runtime-deps'))
import json
import httpx
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from vcc2026.remote_ranges import HTTPRangeReader

def main():
    out=ROOT/'reports/candidate_verification'
    url='https://huggingface.co/datasets/Xaira-Therapeutics/X-Atlas-Orion/resolve/main/data/HCT116_Batch1.parquet'
    panel=set(pd.read_csv('C:/Users/ferra/vcc2026-data/raw/controls/pert_counts.csv').target_gene)
    axis=set(pd.read_csv('C:/Users/ferra/vcc2026-data/raw/controls/gene_names.csv').gene_name)
    genes=pq.read_table(out/'annotations/orion_gene_metadata.parquet').to_pandas()
    with HTTPRangeReader(url,max_bytes=64*1024**2) as remote:
        f=pq.ParquetFile(remote)
        meta=f.read(columns=['gene_target','sample','pass_guide_filter']).to_pandas()
        valid=meta.loc[meta.pass_guide_filter.eq(True)]
        counts=valid.gene_target.value_counts()
        # A Parquet row group can force a >64 MiB read even for batch_size=8.
        # Use the public HF rows endpoint for a bounded value sample instead.
        with httpx.Client(timeout=60,follow_redirects=True) as client:
            with client.stream('GET','https://datasets-server.huggingface.co/rows',params={
                'dataset':'Xaira-Therapeutics/X-Atlas-Orion','config':'default','split':'HCT116','offset':0,'length':8}) as response:
                response.raise_for_status()
                body=bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body)>8*1024**2: raise RuntimeError('HF row sample too large')
        payload=json.loads(body)
        (out/'orion_sample_rows.json').write_bytes(body)
        rows=[r['row'] for r in payload['rows']]
        vals=np.concatenate([np.asarray(r['gene_expression']) for r in rows])
        result={'url':url,'remote_size':remote.size,'bytes_transferred':remote.transferred,
                'schema':str(f.schema_arrow),'rows':f.metadata.num_rows,'row_groups':f.metadata.num_row_groups,
                'valid_dual_guide_cells':len(valid),'explicit_ntc_count':int(counts.get('Non-Targeting',0)),
                'target_hits':sorted(panel & set(counts.index)), 'target_counts':counts.to_dict(),
                'output_gene_overlap':len(axis & set(genes.gene_name)),
                'sample':{'cells':len(rows),'values':len(vals),'finite':bool(np.isfinite(vals).all()),
                          'source':'https://datasets-server.huggingface.co/rows','bytes':len(body),
                          'nonnegative':bool((vals>=0).all()),'integer':bool((vals==np.rint(vals)).all()),
                          'paired_lists':all(len(r['gene_token_id'])==len(r['gene_expression']) for r in rows)}}
    (out/'orion_probe.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['target_counts','target_hits','schema']},indent=2))
    print('Observed panel coverage:',len(result['target_hits']))

if __name__=='__main__': main()
