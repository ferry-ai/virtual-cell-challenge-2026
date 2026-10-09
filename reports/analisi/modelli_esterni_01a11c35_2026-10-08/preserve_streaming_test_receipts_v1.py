"""Preserve new AMMI receipts under distinct names and restore historical ridge logs."""
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
for revision in range(1,5):
    source=HERE/('streaming_tests_r%d.txt'%revision)
    destination=HERE/('ammi_streaming_tests_r%d.txt'%revision)
    if destination.exists():raise FileExistsError(destination)
    with destination.open('xb') as stream:stream.write(source.read_bytes())
    relative=source.relative_to(ROOT).as_posix()
    historical=subprocess.run(['git','show','HEAD:'+relative],cwd=ROOT,check=True,capture_output=True).stdout
    source.write_bytes(historical)
print('Preserved four AMMI receipts and restored four historical ridge receipts.')
