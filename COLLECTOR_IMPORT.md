# Verified club imports

The manager-only Collector page accepts complete, visually reviewed club results.
Legacy schemas 1 and 2 remain ClubGG-only. Schema 3 explicitly identifies the
network as `clubgg` or `pokerbros`; club IDs are matched within that network.

Example shape (replace with actual reviewed data):

```json
{
  "schema_version": 3,
  "network": "pokerbros",
  "club_code": "186912",
  "observed_at": "2026-11-05T15:00:00Z",
  "complete": true,
  "club_identity_verified": true,
  "running_tables_checked": true,
  "end_of_list_verified": true,
  "all_rows_verified": true,
  "tables": [
    {"table_name": "Example", "game": "PLO5", "players": "2/6",
     "blinds": "0.5/1", "buyin": "50", "tags": []}
  ]
}
```

Use real observation times. Never mark a partial or uncertain list complete.
An empty list additionally requires `empty_club_verified: true`.
Up to 50 reviewed rows are allowed per club. Only occupied tables at blinds
of at least 0.25/0.50 remain active. Older or equal conflicting observations
cannot replace newer ones. Absent tables are archived, not silently retained.
The existing ordinary Host table limits are unchanged.

PokerBros may display a straddle without its numeric amount, for example
`0.5/1/Str` or `1/2/Str(0.4)`. Preserve the visible notation instead of guessing
a straddle amount. Required Hi-Lo game variants use `required_features: ["hi_lo"]`;
optional features can remain empty when the operator requests no tags.

Paste JSON into **Apply one verified local result**, then verify the page's
receipt. For folder polling, schema 3 filenames include the network:
`club-pokerbros-186912.json` or `club-clubgg-273007.json`. Legacy ClubGG files
retain `club-273007.json`. This avoids collisions across applications.

The browser sends structured table data only, using the current manager
session and CSRF protection. No screenshots, passwords, or external credentials
belong in a result file.
