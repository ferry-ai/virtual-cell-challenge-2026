"""Private Kaggle push with bounded, bearer-safe diagnostics only."""
import json
import re
import sys
from kaggle.api.kaggle_api_extended import KaggleApi


def safe(value):
    text=str(value)
    text=re.sub(r'https?://\S+', '[URL REDACTED]', text)
    text=re.sub(r'[A-Za-z0-9+/=_-]{100,}', '[OPAQUE VALUE REDACTED]', text)
    return text[:1600]


if __name__=='__main__':
    api=KaggleApi();api.authenticate()
    try:
        result=api.kernels_push(sys.argv[1],None,None)
        error=getattr(result,'error',None)
        invalid=getattr(result,'invalidKernelSources',None)
        print(json.dumps(dict(accepted=result is not None and not error and not invalid,
            error=safe(error) if error else None,
            version=getattr(result,'versionNumber',None),
            invalid_kernel_sources=getattr(result,'invalidKernelSources',None))))
        if result is None or error or invalid:sys.exit(1)
        print('successfully pushed')
    except Exception as exc:
        response=getattr(exc,'response',None)
        message=''
        if response is not None:
            try: message=response.json().get('error',{}).get('message','')
            except (ValueError,AttributeError): pass
        print(json.dumps(dict(exception=type(exc).__name__,http_status=getattr(response,'status_code',None),
            message=safe(message),detail=safe(exc))))
        sys.exit(1)
