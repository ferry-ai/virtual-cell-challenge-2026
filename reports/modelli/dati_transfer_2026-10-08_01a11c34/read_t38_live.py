"""Bounded read-only live-log snapshot; sanitized operational events only."""
import argparse
import json
import re
import time
from percorso import HERE,read,write_new,now
from quick_generation_cloud import api_for_owner


def main(revision,label):
    folder=HERE/'cloud_delivery'/revision;proof=read(folder/'prepared.json')
    source=proof['slug'];api=api_for_owner(proof['owner']);events=[]
    from kaggle.api.kaggle_api_extended import KaggleEnv
    result=dict(utc=now(),source=source)
    try:
        with api.build_kaggle_client() as client:
            http=client._http_client;http._init_session()
            base=http._endpoint if http._env==KaggleEnv.PROD else http._endpoint+'/api'
            headers=dict(http._session.headers);headers['Accept']='text/event-stream, */*';headers.pop('Content-Type',None)
            with http._session.get(base+'/v1/kernels/logs/stream/'+source,stream=True,headers=headers,
                                  auth=http._session.auth,timeout=(10,8)) as response:
                result['http_status']=response.status_code;response.raise_for_status();started=time.monotonic()
                for line in response.iter_lines(chunk_size=256,decode_unicode=True):
                    if isinstance(line,bytes):line=line.decode('utf-8',errors='replace')
                    if line and line.startswith('data:'):
                        text=line[5:].strip()
                        if text=='END_OF_LOG':break
                        try:
                            event=json.loads(text);data=event.get('data','')
                            if any(s in data for s in ('"stage"','sha256','REFUSING','Error:',
                                    'validating','verifying','matches','archive','peak','error','FAILED','PASSED')):
                                events.append(dict(time=event.get('time'),data=re.sub(r'https?://[^\s"<>]+','[URL REDACTED]',data)))
                        except ValueError:pass
                    if time.monotonic()-started>25 or len(events)>500:break
    except Exception as exc:
        result['read_ended_with']=type(exc).__name__
    result.update(events=events,utc_complete=now())
    write_new(folder/('live_log_'+label+'.json'),result)
    print(json.dumps(dict(utc_complete=result['utc_complete'],events=events[-10:],
        read_ended_with=result.get('read_ended_with')),ensure_ascii=True))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('revision');p.add_argument('label');a=p.parse_args()
    main(a.revision,a.label)
