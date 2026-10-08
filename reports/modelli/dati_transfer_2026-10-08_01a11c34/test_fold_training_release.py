"""Fold metadata fixtures enforce upstream target exclusion and full context coverage."""
import copy
import hashlib
import math
import unittest
from build_fold_training_release import transform


class FoldViewTests(unittest.TestCase):
    def fixture(self, regime='production', fold='C'):
        visible = next('T'+str(i) for i in range(100) if int(hashlib.sha256(('T'+str(i)).encode()).hexdigest(), 16) % 5)
        rows = [('held', 'K562', 'experiment1'), ('clone1', 'iPSC', 'experiment2'),
                ('clone2', 'iPSC', 'experiment2'), ('neuron', 'neuron', 'experiment3')]
        chunks = [dict(path='UNRESOLVED_MOUNT/'+cid, producer='p/'+cid, producer_file='chunk.npz',
            context_id=cid, context_group=group, identity=dict(study=study), targets=[visible],
            weights=[.25], sha256=cid, bytes=1) for cid, group, study in rows]
        parent = dict(regime=regime, chunks=chunks, genes=['G1'], excluded_targets=[], excluded=[],
                      provenance=[dict(producer=c['producer']) for c in chunks])
        split = dict(id=fold+'-K562', regime=fold, held_groups=['K562'], hidden_targets=['HIDDEN'] if fold == 'J' else [],
                     protected_units=['h1_test'], group_aliases={})
        return parent, split

    def test_all_nonheld_contexts_and_chunk_contents_survive_with_equal_experiment_mass(self):
        parent, split = self.fixture(); saved = copy.deepcopy(parent)
        view, proof = transform(parent, split)
        self.assertEqual(parent, saved)
        self.assertEqual(set(view['expected_rows_by_context']), {'clone1', 'clone2', 'neuron'})
        self.assertEqual([c['weights'][0] for c in view['chunks']], [.25, .25, .5])
        for a, b in zip(parent['chunks'][1:], view['chunks']):
            self.assertEqual({k:v for k,v in a.items() if k != 'weights'}, {k:v for k,v in b.items() if k != 'weights'})
        self.assertEqual(proof['removed_rows'], 1)
        self.assertTrue(math.isclose(proof['total_row_mass'], 1.))

    def test_J_requires_already_filtered_parent_and_rejects_hidden_hash_component(self):
        parent, split = self.fixture('production', 'J')
        with self.assertRaisesRegex(ValueError, 'upstream target-excluded'):
            transform(parent, split)
        parent['regime'] = 'T'
        transform(parent, split)
        hidden = next('T'+str(i) for i in range(100) if int(hashlib.sha256(('T'+str(i)).encode()).hexdigest(), 16) % 5 == 0)
        parent['chunks'][-1]['targets'] = [hidden]
        with self.assertRaisesRegex(ValueError, 'hidden response'):
            transform(parent, split)

    def test_alias_and_protected_context_do_not_escape_exclusion(self):
        parent, split = self.fixture()
        parent['chunks'][0]['context_group'] = 'K562_ALIAS'
        split['group_aliases'] = {'K562_ALIAS': 'K562'}
        view, _ = transform(parent, split)
        self.assertEqual(view['excluded_contexts'], ['K562', 'K562_ALIAS'])
        parent['chunks'][-1]['protected'] = True
        with self.assertRaisesRegex(ValueError, 'protected context'):
            transform(parent, split)


if __name__ == '__main__':
    unittest.main()
