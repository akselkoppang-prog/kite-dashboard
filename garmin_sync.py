"""
Sync new kite/kiteboarding/snowkiting activities from Strava into
kite_data_clean.json.gz.

Garmin devices auto-sync activities to Strava, so pulling from the Strava
REST API covers everything recorded on Garmin.

Credentials are read from a local .env file via python-dotenv
(STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN). Copy
.env.example to .env and fill in your own values (see README.md for how to
obtain them) — never commit .env or hardcode credentials here.

Usage:
    python garmin_sync.py
"""
import os
import sys
import gzip
import json
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

from extract_full import get_location, classify

TOKEN_URL = 'https://www.strava.com/oauth/token'
API_BASE = 'https://www.strava.com/api/v3'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'kite_data_clean.json.gz')
SYNCED_FILE = os.path.join(BASE_DIR, 'last_synced.txt')

KITE_SPORT_TYPES = {'kitesurf', 'kiteboarding', 'windsurf'}


def refresh_access_token(client_id, client_secret, refresh_token):
    resp = requests.post(TOKEN_URL, data={
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()['access_token']


def is_kite_activity(activity):
    name = (activity.get('name') or '').lower()
    if 'kite' in name:
        return True
    if (activity.get('sport_type') or '').lower() in KITE_SPORT_TYPES:
        return True
    if (activity.get('type') or '').lower() in KITE_SPORT_TYPES:
        return True
    return False


def fetch_all_activities(access_token, per_page=200):
    headers = {'Authorization': f'Bearer {access_token}'}
    activities = []
    page = 1
    while True:
        resp = requests.get(f'{API_BASE}/athlete/activities', headers=headers,
                             params={'per_page': per_page, 'page': page}, timeout=30)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        activities.extend(batch)
        page += 1
    return activities


def fetch_streams(access_token, activity_id):
    headers = {'Authorization': f'Bearer {access_token}'}
    resp = requests.get(
        f'{API_BASE}/activities/{activity_id}/streams',
        headers=headers,
        params={'keys': 'latlng,altitude,velocity_smooth,heartrate,time', 'key_by_type': 'true'},
        timeout=30,
    )
    if resp.status_code == 404:
        return {}
    resp.raise_for_status()
    return resp.json()


def downsample(lst, n=500):
    if len(lst) <= n:
        return lst
    step = max(1, len(lst) // n)
    return lst[::step]


def process_activity(activity, streams):
    """Build (session_dict, key, track_pts, timeseries_dict) matching the
    schema already used in kite_data_clean.json.gz, from a Strava activity
    summary + its GPS/HR/altitude streams."""
    activity_id = activity['id']
    key = f'strava_{activity_id}'

    start_str = activity.get('start_date')  # UTC ISO 8601
    if not start_str:
        return None
    dt = datetime.strptime(start_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    ts_start = int(dt.timestamp())

    dist_km = (activity.get('distance') or 0) / 1000
    if dist_km < 3:
        return None

    dur_min = (activity.get('elapsed_time') or 0) / 60

    latlng = (streams.get('latlng') or {}).get('data') or []
    altitude = (streams.get('altitude') or {}).get('data') or []
    velocity = (streams.get('velocity_smooth') or {}).get('data') or []
    heartrate = (streams.get('heartrate') or {}).get('data') or []
    time_s = (streams.get('time') or {}).get('data') or []

    n = len(time_s) or len(latlng) or len(velocity)
    track_pts, speed_ts, hr_ts, alt_ts = [], [], [], []
    for i in range(n):
        t = time_s[i] if i < len(time_s) else None
        rel_min = round(t / 60, 1) if t is not None else None
        spd_kmh = round(velocity[i] * 3.6, 1) if i < len(velocity) and velocity[i] is not None else None
        alt_m = round(altitude[i], 1) if i < len(altitude) and altitude[i] is not None else None
        hr_val = heartrate[i] if i < len(heartrate) and heartrate[i] else None

        if i < len(latlng) and latlng[i]:
            lat, lon = latlng[i]
            if lat and lon and abs(lat) <= 85 and abs(lon) <= 179:
                track_pts.append({'lat': round(lat, 5), 'lon': round(lon, 5),
                                   'spd': spd_kmh or 0, 'alt': alt_m})

        if rel_min is not None:
            speed_ts.append([rel_min, spd_kmh])
            hr_ts.append([rel_min, hr_val])
            alt_ts.append([rel_min, alt_m])

    if track_pts:
        lats = [p['lat'] for p in track_pts]
        lons = [p['lon'] for p in track_pts]
        clat, clon = sum(lats) / len(lats), sum(lons) / len(lons)
        alts_valid = [p['alt'] for p in track_pts if p['alt'] is not None]
        avg_alt = round(sum(alts_valid) / len(alts_valid)) if alts_valid else None
        min_alt = round(min(alts_valid)) if alts_valid else None
        max_alt = round(max(alts_valid)) if alts_valid else None
    else:
        clat = clon = avg_alt = min_alt = max_alt = None

    nonzero_speeds = [v for v in velocity if v]
    avg_kmh = round((sum(nonzero_speeds) / len(nonzero_speeds)) * 3.6, 1) if nonzero_speeds else (
        round(activity['average_speed'] * 3.6, 1) if activity.get('average_speed') else None)
    max_kmh = round(max(velocity) * 3.6, 1) if velocity else (
        round(activity['max_speed'] * 3.6, 1) if activity.get('max_speed') else None)

    avg_hr = round(activity['average_heartrate']) if activity.get('average_heartrate') else None
    max_hr = round(activity['max_heartrate']) if activity.get('max_heartrate') else None

    location = get_location(clat, clon) if clat is not None else (activity.get('name') or 'Unknown')
    sport_type = classify(clat, clon)

    has_hr = any(v is not None for _, v in hr_ts)
    has_alt = any(v is not None for _, v in alt_ts)

    if len(track_pts) > 500:
        step = len(track_pts) // 500
        track_pts = track_pts[::step]

    session = {
        'filename': key,
        'date': dt.strftime('%Y-%m-%d'), 'year': dt.year, 'month': dt.month,
        'duration_min': round(dur_min, 1),
        'distance_km': round(dist_km, 2),
        'avg_speed_kmh': avg_kmh, 'max_speed_kmh': max_kmh,
        'avg_hr': avg_hr, 'max_hr': max_hr, 'calories': activity.get('calories'),
        'avg_alt': avg_alt, 'min_alt': min_alt, 'max_alt': max_alt,
        'total_ascent': round(activity['total_elevation_gain']) if activity.get('total_elevation_gain') else None,
        'total_descent': None,
        'avg_temp': activity.get('average_temp'),
        'location': location, 'sport_type': sport_type,
        'centroid_lat': round(clat, 4) if clat is not None else None,
        'centroid_lon': round(clon, 4) if clon is not None else None,
        'start_timestamp': ts_start,
        'has_hr': has_hr, 'has_alt': has_alt,
        'activity_id': activity_id,
        'wind_dir': None, 'kite_size': None, 'board': None,
        'notes': activity.get('description') or '',
    }
    timeseries = {
        'speed': downsample(speed_ts),
        'hr': downsample(hr_ts) if has_hr else [],
        'alt': downsample(alt_ts) if has_alt else [],
    }
    return session, key, track_pts, timeseries


def load_existing_data():
    if os.path.exists(DATA_FILE):
        with gzip.open(DATA_FILE, 'rt', encoding='utf-8') as f:
            return json.load(f)
    return {'sessions': [], 'tracks': {}, 'timeseries': {}}


def save_data(data):
    with gzip.open(DATA_FILE, 'wt', encoding='utf-8') as f:
        json.dump(data, f)


def main():
    load_dotenv()
    client_id = os.environ.get('STRAVA_CLIENT_ID')
    client_secret = os.environ.get('STRAVA_CLIENT_SECRET')
    refresh_token = os.environ.get('STRAVA_REFRESH_TOKEN')
    if not (client_id and client_secret and refresh_token):
        print(
            'ERROR: STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET and STRAVA_REFRESH_TOKEN '
            'must be set in a local .env file. Copy .env.example to .env and fill '
            'them in — see README.md for how to obtain them.',
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        access_token = refresh_access_token(client_id, client_secret, refresh_token)
    except requests.HTTPError as e:
        print(f'ERROR: Strava token refresh failed: {e}', file=sys.stderr)
        sys.exit(1)

    print('Fetching activities from Strava...')
    activities = fetch_all_activities(access_token)
    print(f'Fetched {len(activities)} total activities.')

    kite_activities = [a for a in activities if is_kite_activity(a)]
    print(f'Found {len(kite_activities)} kite-related activities.')

    data = load_existing_data()
    data.setdefault('tracks', {})
    data.setdefault('timeseries', {})
    existing_ids = {s.get('activity_id') for s in data['sessions'] if s.get('activity_id')}

    added = 0
    for act in kite_activities:
        activity_id = act.get('id')
        if activity_id is None or activity_id in existing_ids:
            continue

        try:
            streams = fetch_streams(access_token, activity_id)
        except requests.HTTPError as e:
            print(f'WARN: failed to fetch streams for activity {activity_id}: {e}')
            streams = {}

        result = process_activity(act, streams)
        if not result:
            print(f'SKIP: activity {activity_id} too short or missing start time.')
            continue

        session, key, track_pts, timeseries = result
        data['sessions'].append(session)
        data['tracks'][key] = track_pts
        data['timeseries'][key] = timeseries
        existing_ids.add(activity_id)
        added += 1

    data['sessions'].sort(key=lambda x: x['start_timestamp'])
    save_data(data)

    synced_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    with open(SYNCED_FILE, 'w') as f:
        f.write(synced_at)

    print(f'Synced {added} new kite sessions from Strava.')


if __name__ == '__main__':
    main()
