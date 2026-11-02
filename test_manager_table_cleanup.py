import re
import unittest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware
import manager_table_cleanup as clean


class CleanupTests(unittest.TestCase):
    def test_identity_preserves_explicit_and_exact_legacy_club_only(self):
        club=dict(id=18,club_name='VANs',application='ClubGG')
        self.assertTrue(clean.belongs_to(dict(club_subscription_id=18,club='Other'),club))
        self.assertFalse(clean.belongs_to(dict(club_subscription_id=19,club='VANs'),club))
        self.assertTrue(clean.belongs_to(dict(club='VANs',network='clubgg'),club))
        self.assertFalse(clean.belongs_to(dict(club='VANs',network='pppoker'),club))

    def test_preview_signature_is_bound_to_club_and_exact_ids(self):
        a=clean.signature('csrf',18,[1,2,3])
        self.assertEqual(a,clean.signature('csrf',18,[3,2,1]))
        self.assertNotEqual(a,clean.signature('csrf',18,[1,2,4]))
        self.assertNotEqual(a,clean.signature('other',18,[1,2,3]))
        self.assertNotEqual(a,clean.signature('csrf',19,[1,2,3]))

    def db(self,rows):
        db=MagicMock();db.__enter__.return_value=db;db.cursor.return_value.__enter__.return_value=db
        db.fetchone.return_value=dict(id=18,club_name='VANs',application='ClubGG')
        db.fetchall.return_value=rows;db.rowcount=len(rows)
        return db

    def test_atomic_removal_archives_only_previewed_rows(self):
        db=self.db([dict(id=3,club_subscription_id=19),dict(id=4,club_subscription_id=20)])
        with patch.object(clean,'init_db'),patch.object(clean,'_connect',return_value=db):
            self.assertEqual(clean.remove_previewed_tables(18,[3,4]),2)
        writes=[args for args,_ in db.execute.call_args_list if 'DELETE FROM' in args[0]]
        self.assertEqual(len(writes),1)
        self.assertEqual(writes[0][1][0],[3,4])
        self.assertIn('tableradar_removed_club_tables',writes[0][0])
        self.assertNotIn('DELETE FROM club_subscriptions',writes[0][0])
        db.commit.assert_called_once()

    def test_changed_or_protected_preview_never_deletes(self):
        for rows in ([dict(id=3,club_subscription_id=18)],[]):
            db=self.db(rows)
            with patch.object(clean,'init_db'),patch.object(clean,'_connect',return_value=db):
                with self.assertRaises(ValueError):clean.remove_previewed_tables(18,[3])
            self.assertFalse(any('DELETE FROM' in args[0] for args,_ in db.execute.call_args_list))
            db.commit.assert_not_called()

    def test_route_requires_manager_csrf_and_unchanged_preview(self):
        app=FastAPI();app.add_middleware(SessionMiddleware,secret_key='test-only')
        clean.install_routes(app,lambda r:True)
        client=TestClient(app)
        club=dict(id=18,club_name='VANs',application='ClubGG')
        tables=[dict(id=1,club_subscription_id=18,table_name='Kept',players='1/2',club='VANs'),
                dict(id=2,club_subscription_id=19,table_name='Removed',players='1/2',club='Other')]
        with patch.object(clean,'load_active_operator_clubs',return_value=[club]),patch.object(clean,'load_tables',return_value=tables):
            response=client.get('/manager/tables/cleanup?keep_subscription_id=18')
        self.assertIn('Keep 1 tables in VANs',response.text)
        fields=dict(re.findall(r'name="([^"]+)" value="([^"]*)"',response.text))
        fields['confirmation']='DELETE 1 TABLES'
        with patch.object(clean,'remove_previewed_tables',return_value=1) as remove:
            self.assertEqual(client.post('/manager/tables/cleanup',data=fields|{'csrf':'bad'}).status_code,403)
            self.assertEqual(client.post('/manager/tables/cleanup',data=fields|{'table_ids':'1'}).status_code,400)
            remove.assert_not_called()
            self.assertIn('Cleanup completed',client.post('/manager/tables/cleanup',data=fields).text)
            remove.assert_called_once_with(18,[2])
        forbidden=FastAPI();forbidden.add_middleware(SessionMiddleware,secret_key='test-only')
        clean.install_routes(forbidden,lambda r:False)
        self.assertEqual(TestClient(forbidden).get('/manager/tables/cleanup').status_code,403)


if __name__=='__main__':unittest.main()
