# Kite Dashboard

## Garmin Connect sync

1. Copy `.env.example` to `.env` and fill in your Garmin Connect email and password. `.env` is gitignored and never committed.
2. Run `python garmin_sync.py`, or click "🔄 Sync from Garmin" in the app sidebar.
3. The sync fetches your Garmin activities, filters to kite-related sessions, and merges new ones into `kite_data_clean.json.gz`, skipping duplicates by Garmin activity ID.

### 2-step verification (2FA/MFA)

The unofficial `garminconnect` package authenticates with just email/password and does not support Garmin's 2-step verification prompt. If login fails with an authentication error, disable 2-step verification on your Garmin account (Garmin Connect → account settings → security) before syncing.
