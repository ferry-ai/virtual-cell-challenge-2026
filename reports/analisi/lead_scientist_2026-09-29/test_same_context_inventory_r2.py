"""Guard against supplementary-table notes becoming biological entities."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('inventory_r2', Path(__file__).with_name('same_context_inventory_r2.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class InventoryParserTest(unittest.TestCase):
    def test_table_footnote_and_plain_official_axis(self):
        with tempfile.TemporaryDirectory() as tmp:
            table = Path(tmp) / 'table.csv'
            table.write_text('Caption\nsymbol,entrez,group\nGENE1,101,foo\n* Footnote,,\n', encoding='utf-8')
            self.assertEqual(module.symbols(table, 'symbol', 1), ['GENE1'])
            axis = Path(tmp) / 'axis.csv'
            axis.write_text('gene_name\nNA\nGENE2\n', encoding='utf-8')
            self.assertEqual(module.symbols(axis, 'gene_name'), ['NA', 'GENE2'])


if __name__ == '__main__':
    unittest.main()
