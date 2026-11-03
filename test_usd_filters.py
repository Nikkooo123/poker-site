import unittest
from decimal import Decimal
from usd_blinds import normalize_usd_rate,usd_equivalent
from directory_preferences import normalize_filters
from storage import inherit_club_currencies
from views import render_public_card,render_public_page

class UsdFilterTests(unittest.TestCase):
    def test_native_usd_and_unknown_currency(self):
        self.assertEqual(usd_equivalent('5/10','USD')['big_blind'],'10')
        self.assertIsNone(usd_equivalent('5/10','CHIPS'))
        self.assertIsNone(usd_equivalent('5/10',''))
    def test_rate_converts_blinds_and_ante_without_mutating_source(self):
        self.assertEqual(usd_equivalent('5/10(2)','AED','.25'),dict(big_blind='2.50000000',label='≈ 1.25/2.5(0.5) USD'))
        self.assertEqual(usd_equivalent('5/10','USD','.5')['big_blind'],'5.00000000')
    def test_rate_validation(self):
        for value in ['0','-1','NaN','Infinity','1e999','1e-20','abc']:
            with self.subTest(value=value), self.assertRaises(ValueError):normalize_usd_rate(value)
        self.assertIsNone(normalize_usd_rate(''))
    def test_invalid_blinds_and_small_values(self):
        self.assertIsNone(usd_equivalent('unknown','USD'))
        self.assertIsNone(usd_equivalent('0/1','USD'))
        self.assertIn('<0.01',usd_equivalent('0.01/0.02','CHIPS','.01')['label'])
    def test_rates_follow_stable_club_identity(self):
        clubs=[dict(id=1,currency='AED',usd_per_unit='.25'),dict(id=2,currency='USD',usd_per_unit='1')]
        rows=inherit_club_currencies([dict(club_subscription_id=1),dict(club_subscription_id=2)],clubs)
        self.assertEqual([r['usd_per_unit'] for r in rows],['.25','1'])
    def test_preference_defaults_and_validation(self):
        prefs=normalize_filters({})
        self.assertFalse(prefs['usdMode'])
        self.assertEqual(prefs['minPlayers'],'')
        self.assertEqual(normalize_filters(dict(minPlayers='1',maxPlayers='9',usdMode=True))['maxPlayers'],'9')
        for patch in [dict(minPlayers='0'),dict(maxPlayers='10'),dict(minPlayers=2),dict(usdMode='true')]:
            with self.assertRaises(ValueError):normalize_filters(patch)
    def test_guest_card_keeps_only_public_rate_metadata(self):
        html=render_public_card(dict(id=1,blinds='5/10',currency='AED',usd_per_unit='.25',club='Secret Club',table_name='Secret Table'))
        self.assertIn('data-usd-blind="2.50000000"',html)
        self.assertIn('≈ 1.25/2.5 USD',html)
        self.assertIn('tr-usd-equivalent" hidden',html)
        self.assertNotIn('Secret Club',html)
    def test_render_controls(self):
        html=render_public_page([])
        self.assertIn('id="usd-mode" type="checkbox"',html)
        self.assertNotIn('id="usd-mode" type="checkbox" checked',html)
        for identifier in ['players-min','players-max']:
            self.assertIn('id="'+identifier+'"',html)
        self.assertIn('Players minimum',html)
        self.assertIn('Big blind maximum',html)

if __name__=='__main__':unittest.main()
