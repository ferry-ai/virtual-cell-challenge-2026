"""R2 inventory: reject supplementary-table footnotes lacking numeric Entrez IDs."""
import csv
import importlib.util
from pathlib import Path


def symbols(path, column, skip=0):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        for _ in range(skip):
            next(stream)
        reader = csv.DictReader(stream)
        has_entrez = 'entrez' in reader.fieldnames
        return [row[column] for row in reader
                if row.get(column) and
                (not has_entrez or str(row.get('entrez', '')).isdigit())]


if __name__ == '__main__':
    source = Path(__file__).with_name('same_context_inventory_r1.py')
    spec = importlib.util.spec_from_file_location('inventory_r1', source)
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    old.symbols = symbols
    old.main()
