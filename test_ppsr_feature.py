import unittest
from datetime import datetime, timezone
from table_features import ICONS, feature_buttons, render_feature_icon
from collector_sync import validate_snapshot
from views import _render_tags

class PPSRFeatureTests(unittest.TestCase):
    def test_ppsr_renders_and_is_selectable(self):
        self.assertIn('ppsr', ICONS)
        self.assertIn('data-feature="ppsr"', render_feature_icon('ppsr'))
        self.assertIn('PPSR', _render_tags('ppsr,bomb,double_board'))
        self.assertIn('data-value="ppsr"', feature_buttons(['ppsr']))

    def test_ppsr_import_preserves_bomb_and_double_board_for_omaha_and_ofc(self):
        for game, blinds in [('PLO5','0.5/1'),('OFC','0.5')]:
            doc=dict(schema_version=3, network='pppoker', club_code='2978679', observed_at=datetime.now(timezone.utc).isoformat(), complete=True, club_identity_verified=True, running_tables_checked=True, end_of_list_verified=True, all_rows_verified=True, tables=[dict(table_name='Verified table', game=game, players='2/6' if game=='PLO5' else '2/2', blinds=blinds, buyin='20', tags=['ppsr','bomb','double_board'])])
            result=validate_snapshot(doc)['tables'][0]
            self.assertEqual(set(result['tags'].split(',')), {'ppsr','bomb','double_board'})
            self.assertEqual(result['game'],game)

if __name__ == '__main__': unittest.main()
