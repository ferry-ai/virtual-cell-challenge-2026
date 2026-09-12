"""Download small, explicit public annotations, not complete cell atlases."""
from pathlib import Path
import json
import hashlib
import httpx

BASE='https://raw.githubusercontent.com/emdann/GWT_perturbseq_analysis_2025/master/metadata/'
URLS={
 'cd4_data_sharing.md': BASE+'data_sharing_readme.md',
 'cd4_sgrna_library.csv': BASE+'suppl_tables/sgrna_library_metadata.suppl_table.csv',
 'cd4_design.csv': BASE+'sgRNA_library_curated.csv',
 'cd4_sample_metadata.csv': BASE+'suppl_tables/sample_metadata.suppl_table.csv',
 'cd4_experiments.yaml': BASE+'experiments_config.yaml',
 'orion_gene_metadata.parquet': 'https://huggingface.co/datasets/Xaira-Therapeutics/X-Atlas-Orion/resolve/main/metadata/gene_metadata.parquet',
 'orion_tutorial.ipynb': 'https://huggingface.co/datasets/Xaira-Therapeutics/X-Atlas-Orion/resolve/main/tutorials/filter_convert_to_anndata.ipynb',
 'orion_guide_library.csv': 'https://ndownloader.figshare.com/files/57368587',
}

def main():
    root=Path(__file__).resolve().parents[1]/'reports/candidate_verification/annotations'
    root.mkdir(parents=True,exist_ok=True)
    records={}
    with httpx.Client(timeout=60,follow_redirects=True) as client:
        for name,url in URLS.items():
            with client.stream('GET',url) as r:
                r.raise_for_status()
                body=bytearray()
                for c in r.iter_bytes():
                    body.extend(c)
                    if len(body)>12*1024**2: raise ValueError('Annotation budget exceeded')
            (root/name).write_bytes(body)
            records[name]={'url':url,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
            print(name,len(body),flush=True)
    (root/'manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')

if __name__=='__main__': main()
