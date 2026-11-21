import unittest
from test_collector_sync import snapshot
from collector_sync import validate_snapshot
from views import render_public_card,render_admin_card,render_public_page,game_button
from directory_preferences import normalize_filters

class ShortDeckExclusionTests(unittest.TestCase):
    def document(self):
        d=snapshot()|{'schema_version':3,'network':'pppoker'}
        d['tables'][0].update(table_name='Short Deck',game='6+',blinds='5',players='1/6',buyin='',buyin_unavailable_verified=True)
        return d
    def test_import_ignores_short_deck_without_rejecting_complete_club(self):
        d=self.document()
        self.assertEqual(validate_snapshot(d)['tables'],[])
        normal=snapshot()['tables'][0]
        d['tables'].append(normal)
        rows=validate_snapshot(d)['tables']
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['game'],normal['game'])
    def test_hidden_cards_filter_and_saved_preference(self):
        row=self.document()['tables'][0]|{'id':1}
        self.assertEqual(render_public_card(row),'')
        self.assertEqual(render_admin_card(row),'')
        self.assertEqual(game_button('6+'),'')
        self.assertNotIn('6+',normalize_filters({'activeGames':['6+','NLH']})['activeGames'])
        self.assertNotIn('data-game="6+"',render_public_page([row]))

if __name__=='__main__':unittest.main()
