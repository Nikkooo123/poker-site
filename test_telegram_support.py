import os
import unittest
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import telegram_support as tg


class PrivacyTests(unittest.TestCase):
    def setUp(self):
        self.api = Mock()
        self.conn = Mock()
        self.message = dict(chat={'id': -100123, 'type': 'supergroup'}, message_id=23,
            message_thread_id=55, text='Hello', **{'from': {'id': 44, 'first_name': 'Nikita'}})

    def test_internal_discussion_is_not_delivered(self):
        tg.relay_staff(self.conn, self.api, self.message, -100123)
        self.api.call.assert_not_called()
        self.conn.execute.assert_not_called()

    def test_reply_to_another_topic_is_not_delivered(self):
        self.message['reply_to_message'] = {'message_id': 8}
        self.conn.execute.return_value.fetchone.return_value = (1001, 999, 4)
        tg.relay_staff(self.conn, self.api, self.message, -100123)
        self.api.call.assert_not_called()

    def test_only_mapped_customer_gets_signed_reply(self):
        self.message['reply_to_message'] = {'message_id': 8}
        self.conn.execute.return_value.fetchone.return_value = (1001, 55, 4)
        self.api.call.return_value = {'status': 'member'}
        tg.relay_staff(self.conn, self.api, self.message, -100123)
        calls = self.api.call.call_args_list
        self.assertEqual(calls[1].kwargs['chat_id'], 1001)
        self.assertEqual(calls[1].kwargs['text'], 'Nikita · TableRadar · enquiry #4\n\nHello')
        self.assertNotIn('parse_mode', calls[1].kwargs)

    def test_departed_staff_cannot_reply(self):
        self.message['reply_to_message'] = {'message_id': 8}
        self.conn.execute.return_value.fetchone.return_value = (1001, 55, 4)
        self.api.call.return_value = {'status': 'left'}
        tg.relay_staff(self.conn, self.api, self.message, -100123)
        self.assertEqual(self.api.call.call_count, 1)

    def test_bot_receipts_never_loop(self):
        self.message['from']['is_bot'] = True
        self.message['reply_to_message'] = {'message_id': 8}
        tg.relay_staff(self.conn, self.api, self.message, -100123)
        self.api.call.assert_not_called()

    def test_anonymous_staff_are_not_impersonated(self):
        self.message['sender_chat'] = {'id': -100123}
        tg.relay_staff(self.conn, self.api, self.message, -100123)
        self.api.call.assert_not_called()

    def test_reused_link_cannot_switch_to_other_customer(self):
        self.conn.execute.return_value.fetchone.side_effect = [('Website enquiry',), (3, 1001, 55)]
        tg.relay_private(self.conn, self.api, {'chat': {'id': 2002}, 'text': '/start opaque', 'from': {'id': 2002}}, -100123)
        self.api.call.assert_called_once()
        self.assertEqual(self.api.call.call_args.kwargs['chat_id'], 2002)
        self.assertIn('already been used', self.api.call.call_args.kwargs['text'])

    def test_duplicate_update_does_not_redeliver(self):
        self.conn.execute.return_value.fetchone.return_value = None
        context = Mock()
        context.__enter__ = Mock(return_value=self.conn)
        context.__exit__ = Mock(return_value=False)
        with patch.object(tg.repository, 'connection', return_value=context), patch.object(tg, 'API', return_value=self.api):
            tg.process({'update_id': 99, 'message': self.message}, ('secret', 'TableRadarSupportBot', -100123))
        self.api.call.assert_not_called()


class WebhookTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'TELEGRAM_SUPPORT_BOT_TOKEN': 'test-secret',
            'TELEGRAM_SUPPORT_BOT_USERNAME': 'TableRadarSupportBot', 'TELEGRAM_SUPPORT_STAFF_CHAT_ID': '-100123'})
        self.env.start()
        app = FastAPI()
        tg.install_routes(app, lambda r: None)
        self.client = TestClient(app)
        self.headers = {'x-telegram-bot-api-secret-token': tg.webhook_secret('test-secret')}

    def tearDown(self):
        self.env.stop()

    def test_rejects_forged_webhook_before_database_access(self):
        with patch.object(tg, 'process') as process:
            self.assertEqual(self.client.post('/telegram/webhook', json={'update_id': 1}).status_code, 403)
            process.assert_not_called()

    def test_rejects_invalid_or_large_payload(self):
        self.assertEqual(self.client.post('/telegram/webhook', content='[]', headers=self.headers).status_code, 400)
        self.assertEqual(self.client.post('/telegram/webhook', content='x'*131073, headers=self.headers).status_code, 413)

    def test_authenticated_webhook_routes_update(self):
        with patch.object(tg, 'process') as process:
            self.assertEqual(self.client.post('/telegram/webhook', json={'update_id': 1}, headers=self.headers).status_code, 200)
            process.assert_called_once()

    def test_configuration_failure_preserves_old_contact(self):
        with patch.object(tg, '_ready', False):
            self.assertEqual(tg.contact_url(), 'https://t.me/tableradar')
            self.assertEqual(self.client.get('/telegram/contact').status_code, 503)

    def test_listing_contact_requires_sign_in(self):
        result = self.client.get('/telegram/contact/1', follow_redirects=False)
        self.assertEqual(result.status_code, 303)
        self.assertEqual(result.headers['location'], '/signin')

    def test_listing_contact_rechecks_access_on_server(self):
        app = FastAPI()
        tg.install_routes(app, lambda r: {'email': 'customer@example.invalid'})
        with patch('player_access.join_access', return_value=False), patch.object(tg, 'new_intent') as intent:
            self.assertEqual(TestClient(app).get('/telegram/contact/1').status_code, 403)
            intent.assert_not_called()

    def test_listing_context_is_loaded_on_server(self):
        app = FastAPI()
        tg.install_routes(app, lambda r: {'email': 'customer@example.invalid'})
        with patch('player_access.join_access', return_value=True), patch.object(tg, '_ready', True), patch('storage.load_tables', return_value=[{'id': 1, 'club': 'Example', 'table_name': 'Demo'}]), patch.object(tg, 'new_intent', return_value='opaque') as intent:
            response = TestClient(app).get('/telegram/contact/1', follow_redirects=False)
            self.assertEqual(response.headers['location'], 'https://t.me/TableRadarSupportBot?start=opaque')
            self.assertIn('Club: Example', intent.call_args.args[0])
            self.assertNotIn('customer@', intent.call_args.args[0])

    def test_connection_error_does_not_expose_token(self):
        with patch.object(tg.httpx, 'post', side_effect=RuntimeError('test-secret')):
            with self.assertRaises(tg.TelegramError) as error:
                tg.API('test-secret').call('getMe')
            self.assertNotIn('test-secret', str(error.exception))


if __name__ == '__main__':
    unittest.main()
