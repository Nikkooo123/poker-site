"""Run with python -m unittest test_auth_preview. No live DB or OAuth credentials."""
import contextlib
import os
import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.base_client.errors import OAuthError

import main
import player_access
import social_auth
import social_auth_storage as social_store
from auth import auth_storage


class EmailPreviewTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict(os.environ, {
            'PLAYER_TRIAL_ENABLED': 'true', 'FRIENDS_PREVIEW_ENABLED': 'true',
        }))
        self.users = []
        self.stack.enter_context(patch.object(auth_storage, 'load_users', side_effect=lambda: self.users[:]))
        self.stack.enter_context(patch.object(auth_storage, 'save_users', side_effect=lambda users: self.users.__setitem__(slice(None), users)))
        self.stack.enter_context(patch.object(auth_storage.account_db, 'enabled', return_value=False))
        self.stack.enter_context(patch.object(main.verification_delivery, 'email_ready', return_value=False))
        self.client = TestClient(main.app, base_url='https://testserver', follow_redirects=False)

    def signup(self, email='friend@unregistered.example', **fields):
        return self.client.post('/signup', data=dict(username='Friend', email=email,
            password='safe-password-123', confirm_password=fields.get('confirm', 'safe-password-123')))

    def test_registration_without_delivery_and_password_login(self):
        response = self.signup()
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers['location'], '/')
        self.assertNotIn('email_verified_at', self.users[0])
        self.assertFalse(player_access.needs_email_confirmation(self.users[0]))
        self.assertIsNotNone(auth_storage.authenticate_user('friend@unregistered.example', 'safe-password-123'))
        self.assertIsNone(auth_storage.authenticate_user('friend@unregistered.example', 'wrong-password'))
        self.assertNotEqual(self.users[0]['password_hash'], 'safe-password-123')

    def test_duplicate_cannot_replace_password(self):
        self.signup()
        old_hash = self.users[0]['password_hash']
        response = self.signup(' FRIEND@UNREGISTERED.EXAMPLE ')
        self.assertIn('User already exists', response.text)
        self.assertEqual(len(self.users), 1)
        self.assertEqual(self.users[0]['password_hash'], old_hash)

    def test_invalid_email_and_password_mismatch_rejected(self):
        self.assertIn('valid email', self.signup('not-an-email').text)
        self.assertIn('Passwords do not match', self.signup(confirm='different-password').text)
        self.assertEqual(self.users, [])

    def test_form_enabled_in_preview(self):
        text = self.client.get('/signup').text
        self.assertNotIn('<fieldset disabled', text)
        self.assertIn('Email confirmation is not required', text)

    def test_preview_off_restores_verification(self):
        with patch.dict(os.environ, {'FRIENDS_PREVIEW_ENABLED': 'false'}):
            self.assertIn('<fieldset disabled', self.client.get('/signup').text)
            self.assertEqual(self.signup().status_code, 503)
            self.assertEqual(self.users, [])
            self.assertTrue(player_access.needs_email_confirmation({'verification_required': True}))


class GoogleCallbackTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict(os.environ, {'PLAYER_TRIAL_ENABLED': 'true', 'FRIENDS_PREVIEW_ENABLED': 'true'}))
        self.stack.enter_context(patch.object(social_auth, 'configured_providers', return_value=('google',)))
        self.stack.enter_context(patch.object(social_auth, 'callback_url', return_value='https://testserver/auth/google/callback'))
        self.create = self.stack.enter_context(patch.object(social_store, 'create_flow'))
        self.consume = self.stack.enter_context(patch.object(social_store, 'consume_flow', return_value={'purpose': 'signin'}))
        self.resolve = self.stack.enter_context(patch.object(social_store, 'resolve_identity', return_value={
            'email': 'friend@example.test', 'username': 'Friend', 'credential_version': 'v1'}))
        self.stack.enter_context(patch('staff_access.record_customer_login'))
        self.oauth = Mock()
        async def redirect(request, url, **kwargs):
            request.session['oauth_test_state'] = kwargs['state']
            return RedirectResponse('https://accounts.google.com/')
        self.oauth.authorize_redirect = AsyncMock(side_effect=redirect)
        self.oauth.authorize_access_token = AsyncMock(return_value={'id_token': 'validated-by-authlib', 'userinfo': {
            'sub': 'google-subject', 'email': 'friend@example.test', 'email_verified': True, 'name': 'Friend'}})
        self.stack.enter_context(patch.object(social_auth, 'oauth_client', return_value=self.oauth))
        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key='test-only-secret', https_only=True)
        social_auth.install_social_routes(app, lambda request: None)
        self.client = TestClient(app, base_url='https://testserver', follow_redirects=False)
        self.assertEqual(self.client.get('/auth/google').status_code, 307)

    def callback(self):
        return self.client.get('/auth/google/callback?state=test&code=test')

    def test_valid_identity_signs_in_without_trial_gate(self):
        response = self.callback()
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers['location'], '/')
        self.resolve.assert_called_once_with('google', 'google-subject', 'friend@example.test', 'Friend', None)
        self.assertNotIn('validated-by-authlib', response.headers.get('set-cookie', ''))

    def test_unverified_google_email_still_rejected(self):
        self.oauth.authorize_access_token.return_value['userinfo']['email_verified'] = False
        self.assertEqual(self.callback().status_code, 400)
        self.resolve.assert_not_called()

    def test_missing_id_token_rejected(self):
        self.oauth.authorize_access_token.return_value.pop('id_token')
        self.assertEqual(self.callback().status_code, 400)
        self.resolve.assert_not_called()

    def test_state_failure_cannot_reach_token_exchange(self):
        self.consume.side_effect = social_store.PublicAuthError('Sign-in expired. Start again.')
        self.assertEqual(self.callback().status_code, 400)
        self.oauth.authorize_access_token.assert_not_called()

    def test_authlib_rejection_cannot_create_session(self):
        self.oauth.authorize_access_token.side_effect = ValueError('invalid signature or nonce')
        self.assertEqual(self.callback().status_code, 400)
        self.resolve.assert_not_called()

    def test_client_configuration_error_is_diagnosed_without_secrets(self):
        self.oauth.authorize_access_token.side_effect = OAuthError(error='invalid_client', description='SECRET')
        with self.assertLogs('social_auth', level='WARNING') as logs:
            response = self.callback()
        self.assertEqual(response.status_code, 503)
        self.assertIn('reason=invalid_client', ''.join(logs.output))
        self.assertNotIn('SECRET', response.text + ''.join(logs.output))
        self.resolve.assert_not_called()


class IdentityCollisionTests(unittest.TestCase):
    def test_existing_email_is_not_automatically_linked(self):
        conn = Mock()
        conn.execute.side_effect = [None, None, None, Mock(fetchone=lambda: None), Mock(fetchone=lambda: ('existing@example.test',))]
        @contextlib.contextmanager
        def connection():
            yield conn
        with patch.object(social_store.repository, 'connection', connection):
            with self.assertRaisesRegex(social_store.PublicAuthError, 'already exists'):
                social_store.resolve_identity('google', 'new-subject', 'existing@example.test', 'Friend')
        self.assertFalse(any('INSERT INTO tableradar_social_identities' in str(call) for call in conn.execute.call_args_list))


if __name__ == '__main__':
    unittest.main()
