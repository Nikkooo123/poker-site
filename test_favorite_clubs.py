"""No live accounts, database, email or external services are used."""
import copy
import json
import os
import unittest
from unittest.mock import patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware
import directory_preferences as prefs
from favorite_clubs import club_record, club_catalogue, normalize_favorite_clubs
from views import render_public_page, render_public_card
from storage import inherit_club_currencies


TABLE = dict(id=101, club='Aurora', club_subscription_id=42, network='clubgg',
             table_name='Evening table', game='NLH', blinds='1/2', players='5/6', seats=6)
CLUB = club_record(TABLE)


class ClubIdentityTests(unittest.TestCase):
    def test_identity_survives_new_table_and_club_rename(self):
        self.assertEqual(CLUB['key'], club_record(dict(TABLE, id=999))['key'])
        self.assertEqual(CLUB['key'], club_record(dict(TABLE, club='New name'))['key'])

    def test_legacy_names_are_normalized_and_network_scoped(self):
        base = dict(club='  My  Club ', network='clubgg')
        self.assertEqual(club_record(base)['key'], club_record(dict(base, club='my club'))['key'])
        self.assertNotEqual(club_record(base)['key'], club_record(dict(base, network='pokerbros'))['key'])

    def test_legacy_identity_requires_verified_owner_match(self):
        club = dict(id=42, club_name='Aurora', application='ClubGG', owner_telegram='https://t.me/fixtureowner', currency='USD')
        source = dict(TABLE, club_subscription_id=None, owner_telegram='https://t.me/fixtureowner')
        linked = inherit_club_currencies([source], [club])[0]
        self.assertEqual(club_record(linked)['key'], 'club:42')
        unrelated = inherit_club_currencies([dict(source, owner_telegram='https://t.me/differentowner')], [club])[0]
        self.assertIsNone(unrelated.get('club_subscription_id'))

    def test_catalogue_includes_clubs_without_live_tables_and_deduplicates(self):
        catalogue = club_catalogue([TABLE, dict(TABLE, id=102)], [dict(subscription_id=43, club_name='Quiet club', application='PokerBros')])
        self.assertEqual(len(catalogue), 2)
        self.assertEqual({c['key'] for c in catalogue}, {'club:42', 'club:43'})

    def test_favorites_remain_valid_without_any_live_tables(self):
        saved = prefs.normalize_filters(dict(favoriteClubs=[CLUB], onlyFavoriteClubs=True))
        self.assertEqual(saved['favoriteClubs'], [CLUB])
        self.assertEqual(club_catalogue([]), [])
        self.assertEqual(prefs.saved_filters(dict(table_filters=saved))['favoriteClubs'], [CLUB])

    def test_invalid_and_oversized_preferences_are_rejected(self):
        for value in [None, 'club:42', [CLUB, CLUB], [dict(CLUB, key='../../private')], [dict(CLUB, name='x\n')], [dict(CLUB, network='bad')], [CLUB]*101]:
            with self.subTest(value=repr(value)[:60]), self.assertRaises(ValueError):
                normalize_favorite_clubs(value)
        with self.assertRaises(ValueError):
            prefs.normalize_filters(dict(onlyFavoriteClubs='yes'))

    def test_old_filter_shape_has_safe_defaults(self):
        result = prefs.normalize_filters({})
        self.assertEqual(result['favoriteClubs'], [])
        self.assertFalse(result['onlyFavoriteClubs'])

    def test_hidden_clubs_have_no_identity_or_bookmark_button(self):
        text = render_public_card(TABLE, show_club=False)
        self.assertNotIn('Aurora', text)
        self.assertNotIn('club:42', text)
        self.assertNotIn('tr-club-fav-toggle', text)

    def test_known_club_html_is_escaped(self):
        text = render_public_card(dict(TABLE, club='A"><img src=x onerror=alert(1)>'), show_club=True)
        self.assertNotIn('<img src=x', text)
        self.assertIn('&lt;img', text)

    def test_guest_page_does_not_expose_catalogue(self):
        with patch.dict(os.environ, {'FRIENDS_PREVIEW_ENABLED': 'false'}):
            text = render_public_page([TABLE], clubs=[dict(subscription_id=44, club_name='Hidden club', application='ClubGG')])
        self.assertNotIn('Hidden club', text)
        self.assertNotIn('Aurora', text)
        self.assertNotIn('id="manage-favorite-clubs"', text)


class PreferenceRouteTests(unittest.TestCase):
    def setUp(self):
        self.user = dict(email='alice@example.test', table_filters=prefs.normalize_filters(dict(favoriteClubs=[CLUB])))
        self.writes = []
        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key='fixture-secret')
        @app.get('/fixture-session')
        def session(request: Request):
            request.session['account_csrf'] = 'fixture-csrf'
            return {'ready': True}
        prefs.install_preference_routes(app, lambda request: self.user)
        self.client = TestClient(app)
        self.client.get('/fixture-session')
        def update(email, **fields):
            self.writes.append((email, copy.deepcopy(fields)))
            self.user.update(fields)
            return True
        self.patcher = patch.object(prefs, 'update_user', side_effect=update)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def post(self, body, csrf='fixture-csrf'):
        return self.client.post('/account/table-filters', json=body, headers={'x-csrf-token': csrf})

    def test_valid_save_updates_only_current_account(self):
        response = self.post(dict(favoriteClubs=[CLUB], onlyFavoriteClubs=True))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.writes[0][0], 'alice@example.test')
        self.assertTrue(self.user['table_filters']['onlyFavoriteClubs'])
        self.assertEqual(response.headers['cache-control'], 'no-store')

    def test_cached_client_cannot_erase_favorites(self):
        self.assertEqual(self.post(dict(search='Aurora')).status_code, 200)
        self.assertEqual(self.user['table_filters']['favoriteClubs'], [CLUB])

    def test_user_can_explicitly_clear_saved_clubs(self):
        self.assertEqual(self.post(dict(favoriteClubs=[])).status_code, 200)
        self.assertEqual(self.user['table_filters']['favoriteClubs'], [])

    def test_guests_and_bad_csrf_cannot_write(self):
        self.assertEqual(self.post({}, csrf='wrong').status_code, 403)
        self.user = None
        self.assertEqual(self.post({}).status_code, 403)
        self.assertEqual(self.writes, [])

    def test_invalid_payload_cannot_change_existing_preferences(self):
        for body in [dict(email='bob@example.test'), dict(favoriteClubs=[dict(CLUB, key='bad')]), dict(favoriteClubs=[CLUB]*101)]:
            self.assertEqual(self.post(body).status_code, 400)
        self.assertEqual(self.writes, [])


if __name__ == '__main__':
    unittest.main()
