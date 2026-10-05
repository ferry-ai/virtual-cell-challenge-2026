"""Repair mixed legacy/new encoding introduced by the documentation writer."""
from pathlib import Path
p=Path(__file__).resolve().parents[3]/'docs/REGISTRO.md'
s=p.read_text(encoding='utf-8');out=[];i=0
while i<len(s):
    fixed=False
    if s[i] in ('Ã','Â','â','ð'):
        for n in (4,3,2):
            try:
                candidate=s[i:i+n].encode('cp1252').decode('utf-8')
            except (UnicodeEncodeError,UnicodeDecodeError):continue
            if len(candidate)==1:
                out.append(candidate);i+=n;fixed=True;break
    if not fixed:out.append(s[i]);i+=1
p.write_text(''.join(out),encoding='utf-8')
