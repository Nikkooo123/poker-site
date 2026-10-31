import contextlib
import copy
import os
import re
import unittest
from types import SimpleNamespace
from unittest.mock import patch, Mock

import main
import account_membership as accounts
import crypto_orders
import crypto_checkout
import player_access
from auth.profile_view import render_profile
from membership_plans import PLANS, table_limit
import test_auth_preview as fixtures


class PublicPreviewTests(unittest.TestCase):
    setUp = fixtures.EmailPreviewTests.setUp

    def register(self):
        self.assertEqual(fixtures.EmailPreviewTests.signup(self).status_code, 303)
        text = self.client.get('/profile').text
        return re.search(r'name="csrf" value="([^"]+)"', text).group(1)

    def test_switch_roles_without_payment_or_paid_data_mutation(self):
        csrf = self.register()
        self.users[0].update(plan='host',host_tier='starter',is_active=True,
            membership_source='crypto',membership_expires_at='2099-01-01T00:00:00+00:00',
            manual_subscription_id=91,club_application={'club_name':'Existing'})
        original = copy.deepcopy(self.users[0])
        for role in ('player','host','player'):
            response = self.client.post('/account/preview-role', data={'role':role,'csrf':csrf,'email':'other@example.test'})
            self.assertEqual(response.status_code,303)
            current = accounts.membership_state(self.users[0])
            self.assertEqual(current['plan'],role)
            self.assertTrue(current['is_active'])
            self.assertTrue(player_access.entitled(current))
            self.assertTrue(player_access.join_access(current))
            self.assertEqual({k:v for k,v in self.users[0].items() if k!='friends_preview_role'},original)
            self.assertNotIn('staff_role',self.users[0])
        with patch.dict(os.environ,{'FRIENDS_PREVIEW_ENABLED':'false'}):
            restored = accounts.membership_state(self.users[0])
            self.assertEqual(restored['plan'],'host')
            self.assertEqual(restored['host_tier'],'starter')
            self.assertEqual(table_limit(restored),6)

    def test_csrf_guest_invalid_role_and_admin_guards(self):
        csrf=self.register()
        self.assertEqual(self.client.post('/account/preview-role',data={'role':'host','csrf':'wrong'}).status_code,403)
        for role in ('manager','admin','host_starter','host_pro',''):
            self.assertEqual(self.client.post('/account/preview-role',data={'role':role,'csrf':csrf}).status_code,400)
        self.assertEqual(self.client.get('/manager/club-requests/count').status_code,403)
        with patch.dict(os.environ,{'FRIENDS_PREVIEW_ENABLED':'false'}):
            self.assertEqual(self.client.post('/account/preview-role',data={'role':'host','csrf':csrf}).status_code,403)
        self.client.cookies.clear()
        self.assertEqual(self.client.post('/account/preview-role',data={'role':'host','csrf':csrf}).status_code,403)

    def test_manage_membership_and_host_dashboard_work_without_payment(self):
        csrf=self.register()
        text=self.client.get('/profile').text
        self.assertIn('Choose Player — free preview',text)
        self.assertIn('Choose Host — free preview',text)
        for label in ('Host Starter','Host Pro','data-plan="host_starter"','$299','$599'):
            self.assertNotIn(label,text)
        self.client.post('/account/preview-role',data={'role':'host','csrf':csrf})
        response=self.client.get('/host')
        self.assertEqual(response.status_code,200)
        self.assertIn('Submit club for review',response.text)
        self.assertIn('20 active tables',response.text)
        response=self.client.post('/host/club',data=dict(csrf=csrf,owner_name='Test owner',telegram='@fixturehost',club_name='My test club',application='ClubGG',club_code='123',notes='Rules: test games. Rakeback: none.',currency='USD',listing_conditions='accepted'))
        self.assertEqual(response.status_code,303)
        self.assertEqual(self.users[0]['club_application']['club_name'],'My test club')
        self.assertEqual(self.users[0]['club_application']['table_limit'],20)
        self.assertEqual(self.client.get('/manager/club-requests/count').status_code,403)

    def test_hidden_direct_links_and_invoice_creation(self):
        csrf=self.register()
        for url in ('/pay/host_starter','/pay/host_starter/crypto','/pay/host_pro','/pay/host_pro/crypto'):
            self.assertEqual(self.client.get(url).status_code,303)
        self.assertEqual(self.client.post('/payments/crypto/create/host_pro',data={'csrf':csrf}).status_code,403)
        with patch.object(crypto_orders.repository,'connection') as db:
            with self.assertRaises(ValueError):crypto_orders.create('x@example.test','host_starter','BTC','bitcoin')
            db.assert_not_called()
        with patch.dict(os.environ,{'FRIENDS_PREVIEW_ENABLED':'false','PLAYER_TRIAL_ENABLED':'false'}), patch('crypto_checkout.CryptopayClient') as provider:
            self.assertEqual(self.client.get('/pay/host_starter/crypto').status_code,303)
            response=self.client.post('/payments/crypto/create/host_starter',data={'csrf':csrf})
            self.assertEqual(response.status_code,503)
            provider.return_value.request.assert_not_called()

    def test_manager_approval_of_free_host_preserves_paid_membership(self):
        from host_lifecycle import launch_host
        class Result:
            def __init__(self, row=None, rows=None):self.row=row;self.rows=rows or []
            def fetchone(self):return self.row
            def fetchall(self):return self.rows
        class DB:
            def __init__(self):
                self.user=dict(email='owner@example.test',plan='player',is_active=True,
                    membership_source='crypto',membership_expires_at='2099-01-01T00:00:00+00:00',
                    friends_preview_role='host',club_application=dict(submitted_at='request-v1',status='pending',
                    owner_name='Owner',telegram='@owner',club_name='Own club',club_code='123',application='ClubGG',currency='USD'))
                self.inserts=0
            def execute(self,sql,args=None):
                if sql.startswith('SELECT document FROM tableradar_accounts'):return Result((copy.deepcopy(self.user),))
                if sql.startswith('INSERT INTO club_subscriptions'):self.inserts+=1;return Result((123,))
                if sql.startswith('UPDATE tableradar_accounts'):self.user=copy.deepcopy(args[0].obj)
                return Result()
        db=DB()
        @contextlib.contextmanager
        def connection():yield db
        with patch('host_lifecycle.repository.connection',connection):
            self.assertTrue(launch_host('owner@example.test','request-v1',approve=True))
            self.assertEqual(db.user['plan'],'player')
            self.assertEqual(db.user['membership_source'],'crypto')
            self.assertEqual(db.user['membership_expires_at'],'2099-01-01T00:00:00+00:00')
            self.assertEqual(db.user['friends_preview_host']['manual_subscription_id'],123)
            self.assertFalse(launch_host('owner@example.test','request-v1',approve=True))
            self.assertEqual(db.inserts,1)
            self.assertEqual(db.user['plan'],'player')


if __name__=='__main__':unittest.main()
