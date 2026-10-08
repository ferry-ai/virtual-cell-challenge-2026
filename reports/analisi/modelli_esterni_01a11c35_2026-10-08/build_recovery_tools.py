"""Create immutable transport-only revisions of existing preparation tools."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
OWNER = HERE.parents[2]/'reports/modelli/dati_transfer_2026-10-08_01a11c34'


def new(name, text):
    with (HERE/name).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(text)


def main():
    text = (OWNER/'runtime_view_resolver.py').read_text(encoding='utf-8')
    start = text.index("                temp=path.with_suffix('.partial')")
    end = text.index("        item['path']=", start)
    text = text[:start] + "                downloaded += download_verified(locator['url'], path, size, digest)\n" + text[end:]
    text = text.replace('import urllib.request', 'from private_download_v2 import download_verified')
    new('runtime_view_resolver_v2.py', text)
    text = (HERE/'prepare_cloud_fit_v5.py').read_text(encoding='utf-8')
    text = text.replace("'pie_adapter.py','job_preflight.py'", "'pie_adapter.py','job_preflight.py','private_download_v2.py'")
    text = text.replace("OWNER/'runtime_view_resolver.py'", "HERE/'runtime_view_resolver_v2.py'")
    new('prepare_cloud_fit_v6.py', text)
    text = (HERE/'prepare_dataset_bundle.py').read_text(encoding='utf-8')
    text = text.replace('from prepare_cloud_fit_v5 import', 'from prepare_cloud_fit_v6 import')
    text = text.replace("'r4'", "'r5'").replace('01a11c35-r4', '01a11c35-r5').replace('01a11c35 r4', '01a11c35 r5')
    new('prepare_dataset_bundle_v2.py', text)
    text = (HERE/'upload_private_bundle.py').read_text(encoding='utf-8').replace('01a11c35-r4', '01a11c35-r5')
    new('upload_private_bundle_v2.py', text)


if __name__ == '__main__':
    main()
