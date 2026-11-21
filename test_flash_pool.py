import unittest
from test_collector_sync import snapshot
from collector_sync import validate_snapshot,identity
from storage import _normalize_table
from views import render_public_card

class FlashPoolTests(unittest.TestCase):
    def document(self):
        d=snapshot()|{'schema_version':3,'network':'pppoker'}
        d['tables'][0].update(game='NLH',players='12',table_name='FLASH NLH TX 50BB',fast_fold_pool_verified=True)
        return d
    def test_pool_has_verified_count_without_invented_seat_capacity(self):
        row=validate_snapshot(self.document())['tables'][0]
        self.assertEqual((row['players'],row['seats']),('12','pool'))
        self.assertEqual(_normalize_table(row)['seats'],'pool')
        self.assertEqual(identity(row),identity(row|{'players':'15'}))
        self.assertIn('data-players="12"',render_public_card(row|{'id':1}))
    def test_ordinary_table_counts_remain_strict(self):
        for changes in ({'fast_fold_pool_verified':False},{'game':'PLO5'},{'players':'12/12'}):
            d=self.document();d['tables'][0].update(changes)
            with self.subTest(changes=changes),self.assertRaises(ValueError):validate_snapshot(d)
if __name__=='__main__':unittest.main()
