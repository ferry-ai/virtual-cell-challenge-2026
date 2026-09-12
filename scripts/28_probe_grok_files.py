"""Inspect small public files and bounded count samples for the Grok leads."""
from pathlib import Path
import gzip,io,json,zipfile
import httpx,h5py,numpy as np,pandas as pd
from vcc2026.remote_ranges import HTTPRangeReader
ROOT=Path('reports/grok_verification')
URLS={
 'song_features.tsv.gz':'https://ftp.ncbi.nlm.nih.gov/geo/samples/GSM7951nnn/GSM7951413/suppl/GSM7951413_channel1_transcriptome_features.tsv.gz',
 'song_guides.tsv.gz':'https://ftp.ncbi.nlm.nih.gov/geo/samples/GSM7951nnn/GSM7951413/suppl/GSM7951413_channel1_guides_features.tsv.gz',
 'multiome.zip':'https://zenodo.org/api/records/14217683/files/norman-lab-msk/multiomeperturbseq-v0.zip/content',
 'mcf7_readme.txt':'https://raw.githubusercontent.com/theheking/isoform_specific_perturb_seq/main/README.md',
}
results={}
with httpx.Client(timeout=45,follow_redirects=True) as client:
 for name,url in URLS.items():
  try:
   with client.stream('GET',url) as r:
    r.raise_for_status(); body=bytearray()
    for chunk in r.iter_bytes():
     body.extend(chunk)
     if len(body)>8*1024**2: raise ValueError('8 MiB cap exceeded')
   (ROOT/name).write_bytes(body)
   results[name]={'url':url,'bytes':len(body)}
   if name.endswith('.zip'):
    with zipfile.ZipFile(io.BytesIO(body)) as z: results[name]['members']=z.namelist()
   if name.endswith('.gz'):
    plain=gzip.decompress(body).decode()
    (ROOT/name[:-3]).write_text(plain,encoding='utf8')
    results[name]['lines']=len(plain.splitlines())
  except Exception as e: results[name]={'url':url,'error':str(e)}
  print(name,results[name].get('bytes',results[name].get('error')),flush=True)
url='https://www.ebi.ac.uk/biostudies/files/E-MTAB-14567/filtered_feature_bc_matrix.h5'
try:
 with HTTPRangeReader(url,max_bytes=16*1024**2) as remote:
  with h5py.File(remote,'r') as f:
   m=f['matrix']; data=m['data'][:10000]; features=m['features']
   names=features['name'].asstr()[:]
   types=features['feature_type'].asstr()[:]
   results['mcf7_h5']={'url':url,'shape':m['shape'][:].tolist(),'bytes_transferred':remote.transferred,
     'feature_types':pd.Series(types).value_counts().to_dict(),'integer_sample':bool((data==np.rint(data)).all()),
     'nonnegative_sample':bool((data>=0).all()),'feature_names':names.tolist()}
except Exception as e: results['mcf7_h5']={'url':url,'error':str(e)}
(ROOT/'file_probes.json').write_text(json.dumps(results,indent=2),encoding='utf8')
print({k:{a:b for a,b in v.items() if a not in ['members','feature_names']} for k,v in results.items()})
