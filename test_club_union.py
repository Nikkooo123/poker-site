import unittest
from unittest.mock import MagicMock,patch
import club_subscriptions_storage as clubs
import operator_tables
from club_subscriptions_view import render_club_subscriptions_page
from views import render_admin_page


class ClubUnionTests(unittest.TestCase):
    def database(self,row):
        db=MagicMock();db.__enter__.return_value=db;db.cursor.return_value.__enter__.return_value=db
        db.fetchone.return_value=row
        return db

    def test_create_preserves_union_and_literal_none(self):
        for union in ('Friends Union','none',''):
            db=self.database({'id':23})
            with patch.object(clubs,'init_club_subscriptions_db'),patch.object(clubs,'_connect',return_value=db):
                clubs.add_club_subscription(club_name='Gift',application='ClubGG',club_code='123',union_name=union)
            insert=next(args for args,_ in db.execute.call_args_list if args[0].startswith('INSERT'))
            self.assertIn('union_name',insert[0]);self.assertEqual(insert[1][-1],union)

    def test_table_uses_club_union_even_if_form_value_differs_or_is_blank(self):
        for union in ('Friends Union','none',''):
            db=self.database(dict(club_name='Gift',application='ClubGG',currency='USD',owner_name='',owner_telegram='',union_name=union))
            with patch.object(operator_tables,'_connect',return_value=db),patch.object(operator_tables,'require_capacity'),patch.object(operator_tables,'_insert_table') as insert:
                operator_tables.add_operator_table(23,table_name='Table',union_name='wrong',game='PLO4',blinds='1/2',buyin='100',players='1/2')
            self.assertEqual(insert.call_args.args[1]['union_name'],union)

    def test_legacy_club_without_union_keeps_manual_table_value(self):
        db=self.database(dict(club_name='Gift',application='ClubGG',currency='USD',owner_name='',owner_telegram='',union_name=None))
        with patch.object(operator_tables,'_connect',return_value=db),patch.object(operator_tables,'require_capacity'),patch.object(operator_tables,'_insert_table') as insert:
            operator_tables.add_operator_table(23,table_name='Table',union_name='Legacy union',game='PLO4',blinds='1/2',buyin='100',players='1/2')
        self.assertEqual(insert.call_args.args[1]['union_name'],'Legacy union')

    def test_edit_propagates_only_to_linked_tables(self):
        db=self.database({'id':23})
        with patch.object(clubs,'init_club_subscriptions_db'),patch.object(clubs,'_connect',return_value=db):
            clubs.edit_club_subscription(23,union_name='none')
        updates=[args for args,_ in db.execute.call_args_list if args[0].startswith('UPDATE')]
        self.assertEqual(len(updates),2)
        self.assertTrue(all('union_name=COALESCE' in args[0] and args[1][-2:]==('none',23) for args in updates))

    def test_create_and_edit_forms_and_autofill_escape_union(self):
        html=render_club_subscriptions_page([dict(id=23,club_name='Gift',union_name='<Union & Friends>')])
        self.assertEqual(html.count('name="union_name"'),2)
        self.assertIn('&lt;Union &amp; Friends&gt;',html)
        admin=render_admin_page([],manager=True,active_clubs=[dict(subscription_id=23,club_name='Gift',application='ClubGG',union_name='none')])
        self.assertIn('data-union-name="none"',admin)
        self.assertIn('unionField.value=selected.dataset.unionName',admin)
        self.assertNotIn('union_name:"Union name"',admin)

    def test_union_length_validation(self):
        with patch.object(clubs,'init_club_subscriptions_db'),patch.object(clubs,'_connect') as connect:
            with self.assertRaises(ValueError):clubs.add_club_subscription(club_name='Gift',application='ClubGG',club_code='123',union_name='x'*161)
            with self.assertRaises(ValueError):clubs.edit_club_subscription(23,union_name='x'*161)
            connect.assert_not_called()


if __name__=='__main__':unittest.main()
