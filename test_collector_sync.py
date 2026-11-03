import copy
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware
import collector_sync as sync
import collector_bridge as bridge


def snapshot():
    return dict(schema_version=1,club_code='273007',observed_at=datetime.now(timezone.utc).isoformat(),
        complete=True,club_identity_verified=True,running_tables_checked=True,end_of_list_verified=True,all_rows_verified=True,
        tables=[dict(table_name='Active',game='PLO5',players='1/2',blinds='10/20(40)',buyin='2000',tags=['clock'])])


class CollectorSyncTests(unittest.TestCase):
    def test_manager_import_cap_is_100_and_host_plan_stays_20(self):
        from membership_plans import table_limit
        self.assertEqual(table_limit({'host_tier':'pro'}),20)
        doc=snapshot();doc['tables']=doc['tables']*100
        self.assertEqual(len(sync.validate_snapshot(doc)['tables']),100)
        doc['tables'].append(doc['tables'][0])
        with self.assertRaises(ValueError):sync.validate_snapshot(doc)

    def test_partial_icons_add_confirmed_marks_without_erasing_other_marks(self):
        doc=snapshot();doc['schema_version']=2
        doc['tables'][0].update(features_verified=False,confirmed_tags=['clock','vpip 35%'])
        row=sync.validate_snapshot(doc)['tables'][0]
        self.assertEqual(row['tags'],'clock,vpip 35%')
        self.assertEqual(sync.update_tags('bomb,vpip 20%',row),'bomb,clock,vpip 35%')
        doc['tables'][0]['confirmed_tags']=['invented']
        with self.assertRaises(ValueError):sync.validate_snapshot(doc)

    def test_hilo_is_a_required_variant_and_is_preserved_without_optional_icons(self):
        doc=snapshot();doc['schema_version']=2
        doc['tables'][0].update(required_features=['hi_lo'],features_verified=False)
        row=sync.validate_snapshot(doc)['tables'][0]
        self.assertEqual(row['tags'],'hi_lo')
        self.assertEqual(sync.update_tags('clock',row),'clock,hi_lo')
        self.assertNotEqual(sync.identity(row),sync.identity(row|{'tags':'','required_features':''}))
        normal=row|{'required_features':''}
        self.assertEqual(sync.update_tags('clock,hi_lo',normal),'clock')
        doc['tables'][0]['required_features']=['unknown']
        with self.assertRaises(ValueError):sync.validate_snapshot(doc)

    def test_minimum_blinds_are_inclusive_and_ante_does_not_qualify(self):
        for blinds,expected in [('0.25/0.50',1),('0.25/0.5(10)',1),('0.50/1',1),('0.5/1(2)',1),('1/2',1),('0.24/0.50(10)',0),('0.25/0.49(10)',0),('0.10/0.20(10)',0)]:
            doc=snapshot();doc['tables'][0]['blinds']=blinds
            self.assertEqual(len(sync.validate_snapshot(doc)['tables']),expected,blinds)

    def test_incomplete_stale_future_and_unverified_empty_rejected_before_database(self):
        documents=[]
        for flag in ('complete','club_identity_verified','running_tables_checked','end_of_list_verified','all_rows_verified'):
            documents.append(snapshot()|{flag:False})
        documents += [snapshot()|{'observed_at':(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()},
                      snapshot()|{'observed_at':(datetime.now(timezone.utc)-timedelta(minutes=11)).isoformat()},
                      snapshot()|{'tables':[]}, snapshot()|{'schema_version':True}]
        with patch.object(sync,'_connect') as connect:
            for doc in documents:
                with self.assertRaises(ValueError):sync.apply_snapshot(doc)
            connect.assert_not_called()

    def test_only_positive_player_tables_survive(self):
        doc=snapshot();doc['tables'].append(doc['tables'][0]|{'table_name':'Empty','players':'0/2'})
        self.assertEqual(len(sync.validate_snapshot(doc)['tables']),1)
        self.assertEqual(sync.validate_snapshot(snapshot()|{'tables':[],'empty_club_verified':True})['tables'],[])

    def test_unverified_features_are_not_treated_as_verified_empty_tags(self):
        doc=snapshot();doc['tables'][0]['features_verified']=False
        row=sync.validate_snapshot(doc)['tables'][0]
        self.assertFalse(row['features_verified']);self.assertEqual(row['tags'],'')
        doc['tables'][0]['features_verified']='yes'
        with self.assertRaises(ValueError):sync.validate_snapshot(doc)

    def test_ambiguous_fields_fail_closed(self):
        for field,value in [('game','PLO?'),('players','1/?'),('players','3/2'),('buyin','NaN'),('tags',['unknown']),('blinds','?')]:
            doc=snapshot();doc['tables'][0][field]=value
            with self.assertRaises(ValueError):sync.validate_snapshot(doc)

    def test_duplicate_names_remain_separate_and_replays_do_not_multiply(self):
        rows=[snapshot()['tables'][0]|{'id':1,'players':'2/2'},snapshot()['tables'][0]|{'id':2,'players':'1/2'}]
        incoming=sync.validate_snapshot(snapshot())['tables']*2
        updates,creates,removed=sync.reconciliation(rows,incoming)
        self.assertEqual([item[0] for item in updates],[1,2]);self.assertEqual(creates,[]);self.assertEqual(removed,[])
        updates,creates,removed=sync.reconciliation(rows,incoming[:1])
        self.assertEqual(removed,[2])

    def test_identity_normalizes_quotes_and_amounts_but_not_game_or_blinds(self):
        a=snapshot()['tables'][0]|{'table_name':"Kevin's",'buyin':'2000.00'}
        b=a|{'table_name':'Kevin’s','buyin':'2000'}
        self.assertEqual(sync.identity(a),sync.identity(b))
        self.assertNotEqual(sync.identity(a),sync.identity(b|{'game':'PLO6'}))

    def test_atomic_changes_are_placement_scoped_and_archived(self):
        doc=snapshot();db=MagicMock();db.__enter__.return_value=db;db.cursor.return_value.__enter__.return_value=db
        club=dict(id=18,club_name='VANs',application='ClubGG',currency='USD',host_tier='pro')
        old=doc['tables'][0]|{'id':1}
        db.fetchall.side_effect=[[club],[old,old|{'id':2,'table_name':'Gone'}]]
        db.fetchone.return_value=None
        with patch.object(sync,'init_db'),patch.object(sync,'_connect',return_value=db):
            result=sync.apply_snapshot(doc)
        self.assertEqual(result['active'],1);self.assertEqual(result['removed'],1)
        deletes=[args for args,_ in db.execute.call_args_list if 'DELETE FROM poker_tables' in args[0]]
        self.assertEqual(deletes[0][1],(18,[2]));self.assertIn('tableradar_removed_club_tables',deletes[0][0])
        db.commit.assert_called_once()

    def test_route_requires_manager_session_csrf_and_bounded_json(self):
        app=FastAPI();app.add_middleware(SessionMiddleware,secret_key='test-only');bridge.install_routes(app,lambda r:True)
        client=TestClient(app);page=client.get('/manager/collector')
        import re,json
        csrf=json.loads(re.search(r'const csrf=("[^"]+")',page.text)[1])
        with patch.object(bridge,'apply_snapshot',return_value={'applied':True,'active':1}) as apply:
            self.assertEqual(client.post('/manager/collector-sync',json=snapshot()).status_code,403)
            headers={'X-Collector-CSRF':csrf}
            self.assertEqual(client.post('/manager/collector-sync',json=snapshot(),headers=headers).status_code,200)
            self.assertEqual(client.post('/manager/collector-sync',content=b' '*262145,headers=headers|{'Content-Type':'application/json'}).status_code,413)
            self.assertEqual(apply.call_count,1)
        forbidden=FastAPI();forbidden.add_middleware(SessionMiddleware,secret_key='test-only');bridge.install_routes(forbidden,lambda r:False)
        self.assertEqual(TestClient(forbidden).get('/manager/collector').status_code,403)


if __name__=='__main__':unittest.main()
