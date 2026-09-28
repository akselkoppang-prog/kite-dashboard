# Kite Dashboard

## Garmin (via Strava) sync

Garmin devices auto-sync activities to Strava, so this dashboard syncs kite
sessions from the Strava API rather than Garmin Connect directly.

1. Go to https://www.strava.com/settings/api and create an API application.
   Copy the **Client ID** and **Client Secret**.
2. Visit this URL in a browser, replacing `YOUR_ID`:
   `https://www.strava.com/oauth/authorize?client_id=YOUR_ID&redirect_uri=http://localhost&response_type=code&scope=activity:read_all`
3. Approve access. You'll be redirected to `http://localhost/?code=...&scope=...` —
   copy the `code` value from the URL.
4. Exchange the code for a refresh token:
   ```
   POST https://www.strava.com/oauth/token
     client_id=YOUR_ID
     client_secret=YOUR_SECRET
     code=THE_CODE_FROM_STEP_3
     grant_type=authorization_code
   ```
   The response includes a `refresh_token` — this is what `garmin_sync.py` uses
   going forward (it refreshes its own access token automatically on each run).
5. Copy `.env.example` to `.env` and fill in `STRAVA_CLIENT_ID`,
   `STRAVA_CLIENT_SECRET`, and `STRAVA_REFRESH_TOKEN`. `.env` is gitignored
   and never committed.
6. Run `python garmin_sync.py`, or click the "🔄 Sync" button in the top-right
   corner of the dashboard.

The sync fetches your Strava activities, filters to kite-related sessions
(name contains "kite", or sport type is Kitesurf/Kiteboarding/WindSurf), and
merges new ones into `kite_data_clean.json.gz`, skipping duplicates by
Strava activity ID.
