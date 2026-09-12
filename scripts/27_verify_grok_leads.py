"""Bounded metadata verification of new leads in the user-supplied Grok inventory."""
import importlib.util
from pathlib import Path
import sys

path=Path(__file__).with_name('20_verify_candidate_accessions.py')
spec=importlib.util.spec_from_file_location('verify',path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.ENDPOINTS={
    'song_247598':'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE247598&targ=self&form=text&view=full',
    'song_247599':'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE247599&targ=self&form=text&view=full',
    'song_249595':'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE249595&targ=self&form=text&view=full',
    'song_filelist':'https://ftp.ncbi.nlm.nih.gov/geo/series/GSE247nnn/GSE247601/suppl/filelist.txt',
    'song_geo':'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE247601&targ=self&form=text&view=full',
    'song_files':'https://ftp.ncbi.nlm.nih.gov/geo/series/GSE247nnn/GSE247601/suppl/',
    'calu3_geo':'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE208240&targ=self&form=text&view=full',
    'calu3_files':'https://ftp.ncbi.nlm.nih.gov/geo/series/GSE208nnn/GSE208240/suppl/',
    'multiome_zenodo':'https://zenodo.org/api/records/14217682',
    'scperturb_zenodo':'https://zenodo.org/api/records/13350497',
    'mcf7_files':'https://www.ebi.ac.uk/biostudies/api/v1/studies/E-MTAB-14567',
    'crisprqtl_files':'https://www.ebi.ac.uk/biostudies/api/v1/studies/E-MTAB-13324'
}
sys.argv=[sys.argv[0],'--out','reports/grok_verification']
module.main()
