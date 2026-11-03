import time
import unittest
from decimal import Decimal
from unittest.mock import patch
import exchange_rates as fx
from usd_blinds import usd_equivalent

class ExchangeRateTests(unittest.TestCase):
    def snapshot(self, age=0):
        return {'result':'success','base_code':'USD','time_last_update_unix':time.time()-age,
                'rates':{'USD':1,'AED':4,'EUR':.8}}

    def test_foreign_currency_direction_and_override(self):
        with patch.object(fx,'_snapshot',self.snapshot()), patch.object(fx,'urlopen') as fetch:
            self.assertEqual(usd_equivalent('5/10','AED')['big_blind'],'2.50')
            self.assertEqual(usd_equivalent('5/10','EUR')['big_blind'],'12.50')
            self.assertEqual(usd_equivalent('5/10','AED','.5')['big_blind'],'5.00000000')
            fetch.assert_not_called()

    def test_outage_preserves_last_week_and_backs_off(self):
        with patch.object(fx,'_snapshot',self.snapshot(8*86400)), patch.object(fx,'_retry_at',0), patch.object(fx,'urlopen',side_effect=OSError) as fetch:
            self.assertEqual(fx.market_usd_rate('AED'),Decimal('.25'))
            self.assertEqual(fx.market_usd_rate('AED'),Decimal('.25'))
            self.assertEqual(fetch.call_count,1)

    def test_stale_or_unknown_has_no_fake_rate(self):
        with patch.object(fx,'_snapshot',self.snapshot(31*86400)), patch.object(fx,'_retry_at',time.time()+3600):
            self.assertIsNone(fx.market_usd_rate('AED'))
        with patch.object(fx,'_snapshot',self.snapshot()):
            self.assertIsNone(fx.market_usd_rate('XYZ'))

    def test_invalid_provider_response(self):
        for value in [{}, {'result':'error'},self.snapshot(31*86400), self.snapshot()]:
            with self.assertRaises((ValueError,KeyError)):fx.validate(value)

if __name__=='__main__':unittest.main()
