# Friends preview authentication

With `FRIENDS_PREVIEW_ENABLED=true` (the existing default), email/password
registration accepts an email address passing the existing syntax validation
without sending a confirmation code or requiring email delivery credentials.
Signup and Google sign-in return to the directory instead of the trial screen.
Unverified email addresses are **not** marked verified. Existing passwords,
duplicate-account checks, paid access and trial entitlement rules are preserved.
Setting `FRIENDS_PREVIEW_ENABLED=false` restores the existing confirmation gate.

## Validation

Install `requirements.txt`, then run:

```sh
python -m unittest test_auth_preview -v
python test_friends_preview.py
python test_verification_reuse.py
FRIENDS_PREVIEW_ENABLED=false python test_trial_join_access.py
```

The callback tests mock the OAuth client and database boundary. They check that
Authlib rejection cannot authenticate, missing ID tokens and unverified provider
emails are rejected, state failure stops token exchange, and an existing email
is not automatically linked. They are not an end-to-end Google login test.

## Google deployment check

On 2026-10-31, a read-only check of `https://tableradar.net/auth/google` returned
a redirect to Google with callback `https://tableradar.net/auth/google/callback`.
Following it displayed Google's sign-in page without an immediate client or
redirect URI error. `www.tableradar.net` redirects to the canonical host.
This confirms initiation only, not a completed login or working client secret.

The remaining blocker is a reproduced callback failure with hosting logs, or
an owner-run end-to-end Google sign-in. This workspace has no hosting logs,
Google Cloud settings, or authorized test Google credentials. Do not rotate or
share secrets to diagnose this in chat.

Check these settings on the host and Google Cloud if callback fails:

- `SOCIAL_LOGIN_ENABLED=true`, `SOCIAL_LOGIN_ORIGIN=https://tableradar.net`.
- `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` belong to the same Web OAuth client;
  its authorized redirect URI is exactly `https://tableradar.net/auth/google/callback`.
- If the OAuth consent app is in Testing, the friend is an allowed test user;
  Google Workspace policies may also restrict access.
- PostgreSQL `DATABASE_URL` is reachable and the account migration has been applied;
  flow and identity tables require database permissions.
- `SESSION_SECRET` is stable and shared between workers and deployments; do not
  change it between initiating sign-in and the callback.

The callback now logs only the provider and an allowlisted OAuth error category,
never the description, authorization code, tokens, or claims. `invalid_client`
and `unauthorized_client` return a configuration-specific 503. `mismatching_state`
suggests an expired/missing session or interrupted flow; `invalid_grant` needs a
fresh flow and checks of client/callback configuration. Other verification
exceptions still log their class only.

If the email already has a password account, sign in with that password first,
then use My Account > Sign-in options to connect Google. Matching an email alone
never grants access to an existing account. Google still requires an Authlib-
validated OIDC identity and `email_verified=true`.

After review and deployment, test signup with a fresh non-deliverable address,
sign out/in using its password, and complete Google login in a private browser.
Do not consider Google fixed in production until that last step succeeds.
