"""Partition completeness, identity and actual H5AD materialization checks."""
import copy
import unittest
from unittest.mock import patch
import test_materialize as fixture
import materialize_partition as m


class PartitionTests(unittest.TestCase):
    def test_roundtrip(self):
        def run(p, root, out):
            return m.run({**p, 'part': 0, 'parts': 1}, root, out)
        with patch.object(fixture, 'run', run):
            fixture.MaterializeTests('test_counts_identity_nested_levels_and_raw_integrity').test_counts_identity_nested_levels_and_raw_integrity()

    def test_union(self):
        plans = {i: {0: {'probabilities': {'128': .2, '64': .1}}} for i in range(7)}
        receipts = []
        for part in range(3):
            chosen, totals = m.select(plans, part, 3)
            receipts.append(dict(part=part, parts=3, source_indices=list(chosen),
                levels=totals, global_levels={'128':7,'64':7}, total_sources=7,
                unit='fixture', bank_receipt_sha256='a', source_verification='b',
                genes=18533, partition_rule='source_index % parts', complete=True, complete_unit=False))
        self.assertEqual(m.verify_union(receipts), {'128':7,'64':7})
        for bad in (receipts[:2], receipts+[receipts[0]]):
            with self.assertRaises(ValueError): m.verify_union(bad)
        bad = copy.deepcopy(receipts); bad[0]['bank_receipt_sha256'] = 'old'
        with self.assertRaises(ValueError): m.verify_union(bad)
        bad = copy.deepcopy(receipts); bad[0]['levels']['128'] -= 1
        with self.assertRaises(ValueError): m.verify_union(bad)


if __name__ == '__main__': unittest.main()
