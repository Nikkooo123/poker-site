import time
import unittest
from decimal import Decimal
from unittest.mock import patch
from currency_codes import currency_unit,currency_badge
from exchange_rates import market_usd_rate
from usd_blinds import usd_equivalent
from views import render_public_card

class ClubCurrencyUnitTests(unittest.TestCase):
    def test_hundred_ruble_chip_conversion_and_label(self):
        self.assertEqual(currency_unit('100 RUB'),('RUB',Decimal('100')))
        snap={'time_last_update_unix':time.time(),'rates':{'USD':1,'RUB':100}}
        with patch('exchange_rates._snapshot',snap):
            self.assertEqual(market_usd_rate('100 RUB'),Decimal('1'))
            self.assertEqual(market_usd_rate('RUB'),Decimal('0.01'))
            converted=usd_equivalent('0.5/1','100 RUB')
            self.assertEqual(converted['big_blind'],'1')
            self.assertEqual(converted['label'],'≈ 0.5/1 USD')
            card=render_public_card({'id':1,'game':'NLH','blinds':'0.5/1','players':'1/6','buyin':'','network':'pppoker','currency':'100 RUB'})
            self.assertIn('data-usd-blind="1"',card)
            self.assertIn('1 chip = 100 RUB',card)
        self.assertIn('1 chip = 100 RUB',currency_badge('100 RUB'))
    def test_usd_unit_and_explicit_override_are_not_double_scaled(self):
        self.assertEqual(market_usd_rate('100 USD'),Decimal('100'))
        self.assertEqual(Decimal(usd_equivalent('0.5/1','100 RUB','2')['big_blind']),Decimal('2'))
        self.assertEqual(currency_unit('RUB'),('RUB',Decimal('1')))
        self.assertEqual(currency_unit('0 RUB'),('0 RUB',Decimal('1')))
        self.assertEqual(currency_unit('1000001 RUB'),('1000001 RUB',Decimal('1')))

if __name__=='__main__':unittest.main()
