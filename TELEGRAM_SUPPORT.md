# Telegram team support

The website opens a private conversation with the configured bot. The visitor must
press Start and send their message. Each new website link creates a separate forum
topic in a private staff supergroup. Customers never join or receive an invitation
to that group. Website contact context contains listing names, not account email.

Staff reply to the copied customer message (or the case introduction) using
Telegram's Reply action. Only these replies are delivered. Ordinary topic messages
remain internal. The customer sees the bot as sender, with the staff member's
Telegram display name in the reply. Anonymous administrators must switch to their
personal sender identity to reply. Text and common photo/file/audio/video/sticker
messages are supported; edited/deleted Telegram messages are not synchronized.

Set these variables in the existing Render service, never in the repository:

- `TELEGRAM_SUPPORT_BOT_TOKEN`: BotFather token, stored as a Render secret.
- `TELEGRAM_SUPPORT_BOT_USERNAME`: public username without `@`.
- `TELEGRAM_SUPPORT_STAFF_CHAT_ID`: negative supergroup ID.

The bot must be an administrator with Manage Topics in the private group. It does
not need Delete Messages, Ban Users, Invite Users, or Add Administrators. Keep bot
privacy enabled; admin membership allows the bot to receive group replies.

Startup checks the bot identity, group type and permissions, creates separate
PostgreSQL mapping tables, and registers the HTTPS webhook. Authentication uses
a secret header derived from the token. The public contact links change only after
setup succeeds; missing configuration preserves the previous contact.

`/new` starts a separate general enquiry. Reopening an already-used website link
selects its existing case for that Telegram user. Links expire after 24 hours and
cannot be reused by another Telegram user. A new website click creates a new link.
Messages go to the most recently selected enquiry; replies include its number.

Successful Telegram update IDs are deduplicated in PostgreSQL across deployments.
Telegram retries failures. A network failure after Telegram accepts a send but
before the database commits can result in duplicate delivery or an extra topic;
the Bot API does not offer an idempotency key for these methods. No delivery error
logs include the bot token or customer message bodies.

Validation: `python -m unittest test_telegram_support test_auth_preview test_public_membership_preview`.
Live acceptance: open a website contact link, send from the owner's personal
account, verify its new staff topic, reply from TableRadar, and confirm receipt.
Also send an ordinary staff note and verify it does not reach the private chat.
