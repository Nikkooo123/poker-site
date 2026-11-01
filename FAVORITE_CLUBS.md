# My clubs

The table star still bookmarks a specific table. The smaller star in the Club label bookmarks the club, independently of the table's lifetime.

The compact **My clubs** checkbox next to club search filters tables to saved clubs. The **+** button opens the searchable club picker. Saved clubs with no active tables remain listed; new tables from those clubs match automatically. Other filters, including favorite tables, continue to combine with this filter. **Clear filters** clears the filter state without deleting saved clubs or table stars.

Signed-in users keep up to 100 club bookmarks in their existing account `table_filters` JSON document. The existing CSRF-protected preferences route saves them; no database schema migration is required. Guest choices stay in that browser and the picker explains how to sync by signing in. An older cached client cannot erase the new club fields when saving the previous filter shape.

Approved clubs use the stable placement ID, not a live table ID. Legacy tables use a normalized, network-scoped name key. If the existing legacy-owner match proves which approved club a table belongs to, its placement ID is carried into the directory. Bookmarks retain their label and network while a club has no current tables.

Catalogues and bookmark buttons respect the existing directory visibility rules. Club data is whitelisted, HTML-escaped, and picker labels are inserted with `textContent`. Customer preferences cannot choose the account being updated.

The 60-second refresh waits while the club picker is open or the user is typing in a field, so it does not interrupt selection.

## Validation

- `FRIENDS_PREVIEW_ENABLED=false python -m unittest discover -p 'test_*.py'`: 48 tests pass, plus the existing module-level assertions. The legacy membership/trial tests require preview disabled; preview-specific tests set their own environment.
- JavaScript syntax checks pass for the generated directory and club-picker scripts.
- Isolated local browser fixture: save Aurora, enable My clubs, close both of its tables, confirm the club remains saved, then add a new table with a different table ID and confirm it appears automatically.
- Separate browser verifies account-saved choices. Clear filters retains both club bookmarks and existing table stars. A club with no live tables can be found and saved.
- Mobile at 390px: no horizontal page overflow, picker stays within viewport. No production account preferences were modified for these tests.
