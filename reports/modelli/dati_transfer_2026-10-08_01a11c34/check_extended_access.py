"""Read-only account-side native source access check for the extended transfer."""
import json
from percorso import HERE, read, write_new, now, pin
from quick_generation_cloud import api_for_owner


def main():
    plan=read(HERE/'extended_transfer/r1/protocol.json')
    api=api_for_owner('davideferrante11')
    from kaggle.api.kaggle_api_extended import ApiGetKernelRequest
    results=[]
    for slug in sorted({s['producer'] for s in plan['sources']}):
        req=ApiGetKernelRequest();req.user_name,req.kernel_slug=slug.split('/')
        try:
            with api.build_kaggle_client() as client:
                value=client.kernels.kernels_api_client.get_kernel(req)
            results.append(dict(source=slug,native_admissible=True,private=value.metadata.is_private,
                version=value.metadata.current_version_number))
        except Exception as exc:
            results.append(dict(source=slug,native_admissible=False,error_type=type(exc).__name__))
    report=dict(utc=now(),destination='davideferrante11',protocol=pin(HERE/'extended_transfer/r1/protocol.json'),
                sources=results,new_compute=False,downloaded_rna_bytes=0)
    import sys
    write_new(HERE/'extended_transfer/r1'/sys.argv[1],report)
    print(json.dumps(report))


if __name__=='__main__':main()
