"""Read existing metadata from MX; never issue locators or download dataset bodies."""
import json
from percorso import HERE, ROOT, read, pin, write_new, now
from quick_generation_cloud import api_for_owner


def main():
    metadata = ROOT / 'reports/modelli/banca_canonica_2026-10-07/fit/r1/package/kernel-metadata.json'
    required = read(metadata)
    old = read(HERE / 'ammi_private_access_issued_r1.json')
    mounts = read(old['mount_plan']['path'])
    private = read(old['private_locators']['path'])
    api = api_for_owner('davidmaisterx')
    from kaggle.api.kaggle_api_extended import ApiGetKernelRequest, ApiGetDatasetMetadataRequest
    rows = []
    with api.build_kaggle_client() as client:
        for kind, sources in [('kernel', required['kernel_sources']), ('dataset', required['dataset_sources'])]:
            for source in sources:
                row = dict(kind=kind, source=source,
                    in_existing_native_mount_plan=source in mounts[kind + '_sources'],
                    existing_authorized_files=[{k: x[k] for k in ('file', 'bytes', 'sha256')}
                        for x in private['origins'] if x['source'] == source])
                try:
                    if kind == 'kernel':
                        req = ApiGetKernelRequest(); req.user_name, req.kernel_slug = source.split('/')
                        response = client.kernels.kernels_api_client.get_kernel(req)
                        row.update(metadata_readable=True, private=response.metadata.is_private,
                            version=response.metadata.current_version_number,
                            native_admissible=response.metadata.is_private is False or source.startswith('davidmaisterx/'))
                    else:
                        req = ApiGetDatasetMetadataRequest(); req.owner_slug, req.dataset_slug = source.split('/')
                        response = client.datasets.dataset_api_client.get_dataset_metadata(req)
                        if response.error_message:
                            row.update(metadata_readable=False, error_type='ProviderError', native_admissible=False)
                        else:
                            info = json.loads(response.to_json(response.info))
                            visibility = info.get('isPrivate', info.get('is_private'))
                            row.update(metadata_readable=True, private=visibility,
                                native_admissible=True if visibility is False else None,
                                note='metadata readability alone does not establish private cross-account runtime mounting')
                except Exception as exc:
                    row.update(metadata_readable=False, error_type=type(exc).__name__,
                        http_status=getattr(getattr(exc, 'response', None), 'status_code', None),
                        native_admissible=False)
                rows.append(row)
    write_new(HERE / 'ammi_bank_existing_access_r2.json', dict(utc=now(), destination='davidmaisterx',
        source_metadata=pin(metadata), original_mount_plan=old['mount_plan'],
        prior_authorized_locator_receipt=pin(HERE / 'ammi_private_access_issued_r1.json'),
        sources=rows, private_links_issued=0, data_body_bytes_read=0, jobs_launched=0,
        visibility_changed=False, full_runtime_access_verified=False,
        scope='inventory only; existing locator authorization remains restricted to the four private AMMI fits'))
    print(json.dumps(rows))


if __name__ == '__main__':
    main()
