import copy
import unittest
from datetime import date, timedelta
from html.parser import HTMLParser
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient
import account_membership as accounts
import club_subscriptions_storage as store
from club_subscriptions_view import render_club_subscriptions_page
from club_management_view import render_club_delete_form
import main


class Database:
    def __init__(self, users=None, clubs=None):
        self.users = copy.deepcopy(users or {})
        self.clubs = copy.deepcopy(clubs or {})
        self.tables = {key: [f'table-{key}'] for key in self.clubs}
        self.calls = []
        self.result = None
        self.rowcount = 0

    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        self.result = None
        self.rowcount = 0
        if sql.startswith('INSERT INTO club_subscriptions'):
            selected = max(self.clubs, default=0) + 1
            self.clubs[selected] = dict(id=selected, club_name=params[0], owner_email=params[3])
            self.result = {'id': selected}
        elif sql.startswith('SELECT document FROM tableradar_accounts'):
            user = self.users.get(params[0])
            self.result = {'document': copy.deepcopy(user)} if user is not None else None
        elif sql.startswith('SELECT email FROM tableradar_accounts'):
            self.result = {'email': params[0]} if params[0] in self.users else None
        elif sql.startswith('SELECT * FROM club_subscriptions WHERE id=ANY'):
            self.result = [copy.deepcopy(sub) for key, sub in sorted(self.clubs.items())
                           if key in params[0] and sub.get('owner_email', '').strip().lower() == params[1]]
        elif sql.startswith('SELECT * FROM club_subscriptions WHERE id='):
            self.result = copy.deepcopy(self.clubs.get(params[0]))
        elif sql.startswith('UPDATE tableradar_accounts SET document='):
            self.users[params[1]] = copy.deepcopy(params[0].obj)
        elif sql.startswith('DELETE FROM club_subscriptions'):
            self.clubs.pop(params[0], None)
        elif 'WITH removed' in sql:
            for selected in params[0]:
                self.rowcount += len(self.tables.pop(selected, []))
        return self

    def fetchone(self):
        return copy.deepcopy(self.result)

    def fetchall(self):
        return copy.deepcopy(self.result or [])


class Fields(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inputs = []

    def handle_starttag(self, tag, attrs):
        if tag in ('input', 'select', 'textarea'):
            self.inputs.append(dict(attrs))


def fixture():
    club = dict(club_name='Target club', application='ClubGG', submitted_at='request-1', status='approved')
    user = dict(email='owner@example.test', manual_subscription_id=7, host_approved_submission='request-1',
                membership_source='manager', club_application=club, is_active=True, staff_role='manager',
                password_hash='fixture-only', favourite_tables=[17], plan='host')
    sub = dict(id=7, club_name='Target club', application='Club GG', owner_email=user['email'],
               status='active', expires_at=date.today() + timedelta(days=30))
    other = dict(sub, id=8, club_name='Unrelated club')
    return user, sub, other


class ManagerClubTests(unittest.TestCase):
    def run_store(self, db, function, *args, **kwargs):
        with patch.object(store, 'init_club_subscriptions_db'), patch.object(store, '_connect', return_value=db):
            return function(*args, **kwargs)

    def test_fully_blank_creation_needs_no_owner_account_or_request(self):
        db = Database()
        selected = self.run_store(db, store.add_club_subscription, duration_days='', plan='')
        self.assertEqual(selected, 1)
        sql, params = next(call for call in db.calls if call[0].startswith('INSERT'))
        self.assertEqual(params[:5], ('', '', '', '', ''))
        self.assertEqual((params[6] - params[5]).days, 30)
        self.assertIn("'active'", sql)
        self.assertIn('manager_created', sql)
        self.assertFalse(any('tableradar_accounts' in query for query, _ in db.calls))

    def test_arbitrary_contacts_and_multiple_clubs_do_not_grant_account_access(self):
        original = {'email': 'existing@example.test', 'plan': 'player', 'staff_role': 'manager'}
        db = Database(users={original['email']: original})
        for name in ('A', 'B'):
            self.run_store(db, store.add_club_subscription, name, owner_email=original['email'], duration_days='12')
        self.assertEqual(len(db.clubs), 2)
        self.assertEqual(db.users[original['email']], original)
        self.run_store(db, store.add_club_subscription, owner_email='not-yet-registered', duration_days=None)
        self.assertEqual(len(db.clubs), 3)

    def test_days_validation_does_not_turn_blank_into_required_input(self):
        for value in ('0', '-1', '3661', 'not-a-day'):
            db = Database()
            with self.assertRaises(ValueError):
                self.run_store(db, store.add_club_subscription, duration_days=value)
            self.assertEqual(db.calls, [])

    def test_creation_fields_are_optional_and_blank_days_pass_fastapi(self):
        html = render_club_subscriptions_page([], 'csrf')
        parser = Fields()
        parser.feed(html)
        names = {'club_name', 'owner_name', 'owner_telegram', 'owner_email', 'application', 'plan', 'duration_days', 'notes'}
        fields = [item for item in parser.inputs if item.get('name') in names]
        self.assertEqual({item['name'] for item in fields}, names)
        self.assertTrue(all('required' not in item and 'readonly' not in item for item in fields))
        with patch.object(main, 'require_manager', return_value=None), patch.object(main, 'get_current_user', return_value=None), \
                patch.object(main, 'load_club_subscriptions', return_value=[]), patch.object(main, 'add_club_subscription') as create:
            client = TestClient(main.app, base_url='https://testserver')
            try:
                page = client.get('/admin/club-subscriptions')
                tokens = Fields(); tokens.feed(page.text)
                token = next(item['value'] for item in tokens.inputs if item.get('name') == 'csrf')
                response = client.post('/admin/club-subscriptions/add', data=dict.fromkeys(names, '') | {'csrf': token}, follow_redirects=False)
                self.assertEqual(response.status_code, 303)
                self.assertEqual(create.call_args.kwargs['duration_days'], '')
            finally:
                client.close()

    def test_subscription_delete_removes_only_linked_request_and_monitoring(self):
        user, sub, other = fixture()
        db = Database({user['email']: user}, {7: sub, 8: other})
        self.run_store(db, store.delete_club_subscription, 7)
        self.assertNotIn(7, db.clubs)
        self.assertIn(8, db.clubs)
        self.assertNotIn(7, db.tables)
        self.assertIn(8, db.tables)
        changed = db.users[user['email']]
        self.assertNotIn('club_application', changed)
        self.assertNotIn('manual_subscription_id', changed)
        for key in ('password_hash', 'staff_role', 'favourite_tables'):
            self.assertEqual(changed[key], user[key])

    def test_subscription_delete_preserves_newer_request_for_different_club(self):
        user, sub, _ = fixture()
        user['club_application'] = dict(user['club_application'], club_name='Different club', submitted_at='request-2')
        db = Database({user['email']: user}, {7: sub})
        self.run_store(db, store.delete_club_subscription, 7)
        self.assertEqual(db.users[user['email']]['club_application']['club_name'], 'Different club')

    def test_delete_from_requests_removes_linked_subscription(self):
        user, sub, other = fixture()
        db = Database({user['email']: user}, {7: sub, 8: other})
        self.run_store(db, store.delete_club_request_and_subscription, user['email'], 'request-1')
        self.assertNotIn(7, db.clubs)
        self.assertIn(8, db.clubs)
        self.assertNotIn('club_application', db.users[user['email']])

    def test_request_delete_does_not_remove_unrelated_existing_placement(self):
        user, sub, _ = fixture()
        user['club_application'] = dict(user['club_application'], club_name='Another club', submitted_at='new-request')
        db = Database({user['email']: user}, {7: sub})
        self.run_store(db, store.delete_club_request_and_subscription, user['email'], 'new-request')
        self.assertIn(7, db.clubs)
        self.assertIn(7, db.tables)
        self.assertNotIn('club_application', db.users[user['email']])

    def test_stale_request_is_rejected_without_deletion(self):
        user, sub, _ = fixture()
        db = Database({user['email']: user}, {7: sub})
        with self.assertRaisesRegex(ValueError, 'request changed'):
            self.run_store(db, store.delete_club_request_and_subscription, user['email'], 'old-request')
        self.assertIn(7, db.clubs)
        self.assertIn('club_application', db.users[user['email']])

    def test_blank_club_can_be_deleted_without_account(self):
        db = Database(clubs={7: dict(id=7, club_name='', owner_email='')})
        self.run_store(db, store.delete_club_subscription, 7)
        self.assertEqual(db.clubs, {})

    def test_confirmations_escape_names_and_identify_both_panels(self):
        html = render_club_delete_form('/delete', 'csrf', '\"><script>alert(1)</script>', {'email': 'x\"y'})
        self.assertNotIn('<script>', html)
        self.assertIn('onsubmit="return confirm(', html)
        self.assertIn('linked club request', html)
        self.assertIn('Delete club permanently', html)
        html = render_club_subscriptions_page([dict(id=7, club_name='')], 'csrf')
        self.assertIn('Untitled club #7', html)
        self.assertIn('Delete club permanently', html)
        self.assertIn('onsubmit="return confirm(', html)

    def test_delete_route_requires_manager_and_csrf(self):
        app = FastAPI()
        accounts.install_account_routes(app, lambda request: {})
        endpoint = next(route.endpoint for route in app.routes if getattr(route, 'path', '') == '/admin/club-requests/delete-club')
        request = SimpleNamespace(session={'account_csrf': 'correct'})
        for manager, token in ((False, 'correct'), (True, 'wrong')):
            with patch.object(accounts, 'is_manager', return_value=manager), patch.object(store, 'delete_club_request_and_subscription') as remove:
                response = endpoint(request, csrf=token, email='owner@example.test', submitted_at='request-1')
            self.assertEqual(response.status_code, 403)
            remove.assert_not_called()


if __name__ == '__main__':
    unittest.main()
