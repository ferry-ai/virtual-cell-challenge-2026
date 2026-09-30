"""Copy the tested A download path with the three exact B provenance substitutions."""
import ast
from pathlib import Path

here = Path(__file__).parent
source = (here / 'download_stack_cells_r1.py').read_text()
for old, new in [
    ("KERNEL = 'davidmaisterx/vcc-stack-pilot-r1'", "KERNEL = 'davidmaisterx/vcc-stack-variant-b-r1'"),
    ('a2e407961e2aefacd634f17541440bfd1e7035a036658f63cb655a33a9926698',
     'f61f5799d2b8d1c661a705d60bafeb84b3247e72d015b0ff16b5d266726440b0'),
    ("'lead_stack_r1/prediction/'", "'lead_stack_variant_b_r1/prediction/'"),
]:
    if source.count(old) != 1:
        raise ValueError('Original download helper differs; inspect before copying')
    source = source.replace(old, new)
ast.parse(source)
out = here / 'download_stack_b_cells_r1.py'
with out.open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(source)
print(out)
