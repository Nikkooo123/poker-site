import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
from fastapi.responses import HTMLResponse
import main
import club_subscriptions_storage as store
import operator_tables
from club_subscriptions_view import render_club_subscriptions_page


class ClubMetadataTests(unittest.TestCase):
    def test_new_club_identity_is_required_on_server(self):
        complete=dict(club_name='Gift',application='Club GG',club_code='123')
        with patch.object(store,'init_club_subscriptions_db'),patch.object(store,'_connect') as connect:
            for field in complete:
                with self.assertRaises(ValueError):
                    store.add_club_subscription(**(complete|{field:'   '}))
            with self.assertRaises(ValueError):
                store.add_club_subscription(**(complete|{'application':'not-supported'}))
            connect.assert_not_called()

    def test_currency_list_supports_optional_manager_and_required_owner_fields(self):
        from currency_codes import currency_input
        from test_manager_club_controls import Fields
        for required in (True,False):
            fields=Fields();fields.feed(currency_input(required=required))
            search=next(field for field in fields.inputs if 'data-currency-search' in field)
            self.assertEqual('required' in search,required)
            self.assertIn('role="listbox"',currency_input(required=required))

    def test_edit_updates_only_selected_listing_and_tables_not_account_or_dates(self):
        db = MagicMock()
        db.__enter__.return_value = db
        db.cursor.return_value.__enter__.return_value = db
        db.fetchone.return_value = {'id': 23}
        with patch.object(store, 'init_club_subscriptions_db'), patch.object(store, '_connect', return_value=db):
            store.edit_club_subscription(23,club_name='Gift club',owner_name='Friend',
                owner_email='new@example.test',owner_telegram='@new_owner',application='Club GG',currency='usd')
        writes = [(args[0],args[1]) for args,_ in db.execute.call_args_list if args[0].startswith('UPDATE')]
        self.assertEqual(len(writes),2)
        self.assertTrue(all(params[-1]==23 for _,params in writes))
        self.assertIn('owner_contact_email=%s',writes[0][0])
        self.assertNotIn('owner_email=%s',writes[0][0])
        self.assertNotIn('expires_at',writes[0][0])
        self.assertIn('new@example.test',writes[0][1])
        self.assertIn('USD',writes[1][1])
        self.assertIn('https://t.me/new_owner',writes[1][1])
        self.assertFalse(any('UPDATE tableradar_accounts' in args[0] for args,_ in db.execute.call_args_list))

    def test_bad_currency_or_contact_never_opens_database(self):
        with patch.object(store,'init_club_subscriptions_db'),patch.object(store,'_connect') as connect:
            for kwargs in ({'currency':'<USD>'},{'owner_telegram':'https://example.test/evil'},{'application':'unsupported'}):
                with self.assertRaises(ValueError): store.edit_club_subscription(23,**kwargs)
            connect.assert_not_called()

    def test_manager_and_csrf_required_to_edit(self):
        request=SimpleNamespace(session={'account_csrf':'correct'})
        values=dict(club_name='',owner_name='',owner_telegram='',owner_email='',application='',currency='',club_code='',notes='')
        with patch.object(main,'edit_club_subscription') as edit:
            with patch.object(main,'require_manager',return_value=HTMLResponse('Forbidden',status_code=403)):
                self.assertEqual(main.admin_edit_club_subscription(request,23,csrf='correct',**values).status_code,403)
            with patch.object(main,'require_manager',return_value=None):
                self.assertEqual(main.admin_edit_club_subscription(request,23,csrf='wrong',**values).status_code,403)
            edit.assert_not_called()

    def test_creation_currency_and_editable_contact_are_present_and_escaped(self):
        html=render_club_subscriptions_page([dict(id=23,club_name='Gift club',owner_email='account@example.test',
            owner_contact_email='contact@example.test',currency='USD',notes='<script>bad</script>',
            request_club_code='273007')],csrf='test')
        self.assertIn('/23/edit',html)
        self.assertIn('name="currency"',html)
        self.assertIn('contact@example.test',html)
        self.assertNotIn('account@example.test',html)
        self.assertIn('273007',html)
        self.assertIn('&lt;script&gt;',html)
        self.assertNotIn('<script>bad</script>',html)

    def test_table_creation_accepts_missing_owner_contact_and_inherits_currency(self):
        db=MagicMock()
        db.__enter__.return_value=db
        db.cursor.return_value.__enter__.return_value=db
        db.fetchone.return_value=dict(club_name='Gift club',application='Club GG',currency='USD',owner_name='',owner_telegram='')
        with patch.object(operator_tables,'_connect',return_value=db),patch.object(operator_tables,'require_capacity'),patch.object(operator_tables,'_insert_table') as insert:
            operator_tables.add_operator_table(23,table_name='Test',union_name='-none-',game='PLO4',blinds='1/2',buyin='100',players='1/6')
        values=insert.call_args.args[1]
        self.assertEqual(values['currency'],'USD')
        self.assertEqual(values['owner_telegram'],'')
        self.assertEqual(values['club_subscription_id'],23)


if __name__=='__main__': unittest.main()
