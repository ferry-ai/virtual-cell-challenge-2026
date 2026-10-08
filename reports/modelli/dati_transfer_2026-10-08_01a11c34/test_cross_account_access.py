"""Offline fixtures for access routing; never emit or consume real locators."""
import copy
import unittest
from prepare_cross_account_access import transform_routes


class RouteTests(unittest.TestCase):
    def fixture(self):
        chunk = dict(producer='davideferrante11/source', producer_file='one.npz',
                     bytes=12, sha256='frozen', weights=[1], targets=['T'])
        view = dict(chunks=[chunk], split={'hidden':['H']})
        base = dict(kernel_sources=['davideferrante11/source', 'public/source'],
            sources={'davideferrante11/source':dict(chunks=1, bytes=12, route='native_mount')})
        old = dict(files={})
        issued = {'davideferrante11/source/one.npz':dict(bytes=12, sha256='frozen', url='https://example.invalid/fixture')}
        return base, old, view, issued

    def test_only_routes_change_without_mutating_inputs(self):
        base, old, view, issued = self.fixture()
        before = copy.deepcopy((base, old, view, issued))
        result, locators = transform_routes(base, old, view, {'davideferrante11/source'}, issued, 'davidmaisterx')
        self.assertEqual(result['kernel_sources'], ['public/source'])
        self.assertEqual(locators['runtime_owner'], 'davidmaisterx')
        self.assertEqual(locators['files'], issued)
        self.assertEqual((base, old, view, issued), before)

    def test_wrong_hash_missing_and_extra_files_fail(self):
        for mutation in ('hash', 'missing', 'extra', 'http'):
            with self.subTest(mutation=mutation):
                base, old, view, issued = self.fixture()
                key = next(iter(issued))
                if mutation == 'hash': issued[key]['sha256'] = 'changed'
                elif mutation == 'missing': issued.clear()
                elif mutation == 'extra': issued['other/file.npz'] = dict(issued[key])
                else: issued[key]['url'] = 'http://example.invalid/fixture'
                with self.assertRaises(ValueError):
                    transform_routes(base, old, view, {'davideferrante11/source'}, issued, 'davidmaisterx')

    def test_locator_outside_frozen_view_fails(self):
        base, old, view, issued = self.fixture()
        old['files']['unrelated/file.npz'] = dict(bytes=1, sha256='other', url='https://example.invalid/fixture')
        with self.assertRaisesRegex(ValueError, 'outside frozen view'):
            transform_routes(base, old, view, {'davideferrante11/source'}, issued, 'davidmaisterx')


if __name__ == '__main__':
    unittest.main()
