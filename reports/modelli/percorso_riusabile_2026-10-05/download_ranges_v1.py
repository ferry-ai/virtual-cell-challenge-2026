"""Stream the exact cloud product in bounded HTTP ranges, preserving partial bytes.

Kaggle CLI kernels_output uses response.content and loses an interrupted large body.
URLs stay only in memory; metadata and expected SHA come from the verified producer.
"""
import os,json,time
from pathlib import Path
def download(api,job,path,expected_bytes,report):
 import requests
 from kaggle.api.kaggle_api_extended import ApiListKernelSessionOutputRequest
 req=ApiListKernelSessionOutputRequest();req.user_name,req.kernel_slug=job.split('/');req.page_size=100
 files=[]
 while True:
  with api.build_kaggle_client() as c:r=c.kernels.kernels_api_client.list_kernel_session_output(req)
  files.extend(x for x in (r.files or []) if x.file_name=='prediction.vcc')
  if not r.next_page_token:break
  req.page_token=r.next_page_token
 assert len(files)==1,'exact final artifact not unique'
 url=files[0].url
 assert path.stat().st_size<=expected_bytes if path.exists() else True
 start=time.monotonic();last=0
 while (path.stat().st_size if path.exists() else 0)<expected_bytes:
  offset=path.stat().st_size if path.exists() else 0
  end=min(expected_bytes-1,offset+(64<<20)-1)
  with requests.get(url,headers={'Range':f'bytes={offset}-{end}'},stream=True,timeout=(30,120)) as response:
   assert response.status_code==206,'provider did not honor resumable range'
   assert response.headers.get('Content-Range')==f'bytes {offset}-{end}/{expected_bytes}','range identity mismatch'
   with path.open('ab') as output:
    for chunk in response.iter_content(chunk_size=1<<20):
     if not chunk:continue
     assert output.tell()+len(chunk)<=end+1
     output.write(chunk)
     if time.monotonic()-last>10:
      output.flush()
      report('downloading',downloaded_bytes=output.tell(),bytes=expected_bytes,seconds=time.monotonic()-start,method='HTTP ranges; bounded streaming')
      last=time.monotonic()
    output.flush();os.fsync(output.fileno())
  assert path.stat().st_size==end+1,'short range retained; inspect before resume'
