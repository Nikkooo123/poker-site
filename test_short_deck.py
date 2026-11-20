import unittest
from test_collector_sync import snapshot
from collector_sync import validate_snapshot, identity
from views import render_public_card, render_admin_card, game_button
from directory_preferences import normalize_filters

class ShortDeckTests(unittest.TestCase):
    def document(self):
        d=snapshot()|{'schema_version':3,'network':'pppoker'}
        d['tables'][0].update(table_name='250-1000',game='6+',blinds='5',players='1/6',buyin='',buyin_unavailable_verified=True,tags=['ppsr'])
        return d
    def test_verified_short_deck_ante_round_trip(self):
        row=validate_snapshot(self.document())['tables'][0]
        self.assertEqual((row['game'],row['blinds'],row['buyin']),('6+','5',''))
        self.assertIn('ppsr',row['tags'])
        self.assertNotEqual(identity(row),identity(row|{'game':'NLH'}))
        self.assertIn('data-game="6+"',game_button('6+'))
        self.assertEqual(normalize_filters({'activeGames':['6+']})['activeGames'],['6+'])
        for render in (render_public_card,render_admin_card):
            html=render(row|{'id':1,'club':'Irish Stew','network':'pppoker','club_code':'3000687'})
            self.assertIn('Ante 5',html)
    def test_rejects_invalid_ante_and_does_not_relax_holdem(self):
        for stake in ('0','-5','5/10','NaN','Infinity',''):
            d=self.document();d['tables'][0]['blinds']=stake
            with self.subTest(stake=stake),self.assertRaises(ValueError):validate_snapshot(d)
        d=self.document();d['tables'][0]['game']='NLH'
        with self.assertRaises(ValueError):validate_snapshot(d)
        for variant in ('hi_lo','fixed_limit'):
            d=self.document();d['tables'][0]['required_features']=[variant]
            with self.subTest(variant=variant),self.assertRaises(ValueError):validate_snapshot(d)

if __name__=='__main__':unittest.main()
