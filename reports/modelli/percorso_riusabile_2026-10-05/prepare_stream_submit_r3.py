"""Create an immutable streaming successor without changing the candidate or upload."""
from pathlib import Path

here = Path(__file__).resolve().parent
text = (here / 'download_submit_frozen_r2.py').read_text(encoding='utf-8')
text = text.replace('upload_execution_r2', 'upload_execution_r3')
start = text.index(' from kaggle.api.kaggle_api_extended import KaggleApi,ApiGetKernelRequest')
end = text.index(" evidence=HERE/", start)
text = text[:start] + ''' from kaggle.api.kaggle_api_extended import KaggleApi
 a=KaggleApi();a.authenticate()
 prior=HERE/'generation_successors_r1/upload_execution_r2/producer_verified.json'
 verified=json.loads(prior.read_text(encoding='utf-8'))
 assert verified['job']==JOB and verified['version']==1 and verified['matches_launched_code']
 shutil.copy2(prior,RUN/'producer_verified.json')
''' + text[end:]
text = text.replace('DATA.mkdir(parents=True,exist_ok=False)', 'DATA.mkdir(parents=True,exist_ok=True)')
text = text.replace(" (TRIAL/'submission_texts.md').open('x',encoding='utf-8').write(MODEL+'\\n\\n'+DESCRIPTION+'\\n')", " assert (TRIAL/'submission_texts.md').read_text(encoding='utf-8')==MODEL+'\\n\\n'+DESCRIPTION+'\\n'\n assert not (TRIAL/'submit_t31_raw.json').exists(),'inspect existing entry before any upload'")
start = text.index(" with (RUN/'download_stdout.txt')")
end = text.index(" product=DATA/'prediction.vcc'", start)
text = text[:start] + " from download_ranges_v1 import download\n download(a,JOB,DATA/'prediction.vcc',m['bytes'],state)\n" + text[end:]
text = text.replace("'download_returncode':p.returncode", "'download_method':'HTTP ranges; bounded streaming'")
assert 'kernels\',\'output' not in text and 'p.returncode' not in text
compile(text, str(here/'download_submit_frozen_r3.py'), 'exec')
with (here/'download_submit_frozen_r3.py').open('x',encoding='utf-8') as f:
 f.write(text)
print('Streaming successor r3 created; candidate and submit command unchanged.')
