import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import main
import storage
from views import render_admin_card, _render_tags
from table_features import PRIMARY_FEATURES


class AdminFeaturesTests(unittest.TestCase):
    def test_admin_shows_selected_features_without_inline_editor(self):
        html = render_admin_card(dict(id=7, table_name='<Test>', tags='bomb,clock,straddle', players='1/5'), 'csrf-value')
        self.assertIn('aria-label="Table features"', html)
        for key in ('bomb', 'clock', 'straddle'):
            self.assertIn(f'data-feature="{key}"', html)
        self.assertNotIn('Edit features', html)
        self.assertNotIn('/update_table_tags', html)
        self.assertIn('&lt;Test&gt;', html)
        self.assertNotIn('for <Test>', html)

    def test_combined_feature_is_distinct_from_plain_bomb(self):
        self.assertEqual(storage._normalize_tags('double_board_bomb'), 'double_board_bomb')
        html = _render_tags('double_board_bomb')
        self.assertIn('data-feature="double_board_bomb"', html)
        self.assertNotIn('data-feature="bomb"', html)
        self.assertIn('double_board_bomb', PRIMARY_FEATURES)
        self.assertNotIn('cucurucho', PRIMARY_FEATURES)

    def test_update_only_touches_selected_table_features(self):
        conn = MagicMock()
        cur = conn.__enter__.return_value.cursor.return_value.__enter__.return_value
        cur.fetchone.return_value = {'id': 7}
        with patch.object(storage, 'init_db'), patch.object(storage, '_connect', return_value=conn):
            storage.update_table_tags(7, 'bomb,clock,bomb')
        sql, args = cur.execute.call_args.args
        self.assertIn('SET tags=%s', sql)
        self.assertIn('WHERE id=%s', sql)
        self.assertEqual(args, ('bomb,clock', 7))

    def test_rejects_unknown_features_before_database_access(self):
        with patch.object(storage, '_connect') as connect:
            with self.assertRaises(ValueError):
                storage.update_table_tags(7, 'unknown')
            connect.assert_not_called()

    def test_route_rejects_missing_csrf(self):
        request = SimpleNamespace(session={'account_csrf': 'correct'})
        with patch.object(main, 'require_login', return_value=None), patch.object(main, 'update_table_tags') as update:
            response = main.update_table_tags_route(request, 7, ['bomb'], '')
        self.assertEqual(response.status_code, 403)
        update.assert_not_called()

    def test_route_requires_staff_access(self):
        denied = object()
        with patch.object(main, 'require_login', return_value=denied), patch.object(main, 'update_table_tags') as update:
            self.assertIs(main.update_table_tags_route(SimpleNamespace(), 7, ['bomb'], 'csrf'), denied)
        update.assert_not_called()


if __name__ == '__main__':
    unittest.main()
