"""Prepare download only while exact external-submission approval is pending."""
from pathlib import Path
here=Path(__file__).resolve().parent
text=(here/'download_submit_frozen_r3.py').read_text(encoding='utf-8')
text=text.replace('upload_execution_r3','download_execution_r4')
start=text.index(" state('uploading',")
end=text.index("if __name__=='__main__':",start)
text=text[:start]+" state('download_verified_awaiting_submission_approval',sha256=digest,bytes=product.stat().st_size,product=str(product))\n"+text[end:]
assert "'submit'," not in text and 'vcc.exe' not in text
compile(text,str(here/'download_only_frozen_r4.py'),'exec')
with (here/'download_only_frozen_r4.py').open('x',encoding='utf-8') as f:f.write(text)
print('Download only: no VCC executable, upload or entry creation.')
