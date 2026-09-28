"""
Sync new kite/kiteboarding/snowkiting activities from Garmin Connect into
kite_data_clean.json.gz.

Credentials are read from a local .env file (GARMIN_EMAIL, GARMIN_PASSWORD)
via python-dotenv. Copy .env.example to .env and fill in your own values —
never commit .env or hardcode credentials here.

Usage:
    python garmin_sync.py
"""
import io
import os
import sys
import gzip
import json
import zipfile
from datetime import datetime, timezone

from dotenv import load_dotenv
from garminconnect import Garmin, GarminConnectAuthenticationError

from extract_full import (
    parse_fit, get_location, classify, downsample, v_or_none,
    to_alt, to_deg, FIT_EPOCH, INVALID32,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'kite_data_clean.json.gz')
SYNCED_FILE = os.path.join(BASE_DIR, 'last_synced.txt')

KITE_ACTIVITY_TYPES = ('kitesurf', 'kiteboard', 'kiting')


def is_kite_activity(activity):
    """Match Garmin activities that look kite-related by name, activity type,
    or (best-effort) any other text field in the activity payload."""
    name = (activity.get('activityName') or '').lower()
    if 'kite' in name:
        return True
    type_key = ((activity.get('activityType') or {}).get('typeKey') or '').lower()
    if any(k in type_key for k in KITE_ACTIVITY_TYPES):
        return True
    # Best-effort fallback: search the whole activity payload's text for
    # device/app identifiers like "kitesurfr" — Garmin's list response schema
    # for third-party app names varies, so this scans broadly.
    try:
        blob = json.dumps(activity).lower()
    except (TypeError, ValueError):
        blob = ''
    if 'kitesurfr' in blob:
        return True
    return False


def fetch_all_activities(client, page_size=100):
    activities = []
    start = 0
    while True:
        batch = client.get_activities(start, page_size)
        if not batch:
            break
        activities.extend(batch)
        if len(batch) < page_size:
            break
        start += page_size
    return activities


def download_fit_bytes(client, activity_id):
    """Download the original activity file from Garmin Connect and return raw
    .fit bytes, unwrapping the zip container Garmin's ORIGINAL format uses."""
    raw = client.download_activity(activity_id, dl_fmt=Garmin.ActivityDownloadFormat.ORIGINAL)
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            fit_name = next((n for n in zf.namelist() if n.lower().endswith('.fit')), None)
            if fit_name:
                return zf.read(fit_name)
    except zipfile.BadZipFile:
        pass  # already a raw .fit file
    return raw


def process_fit_bytes(raw, activity_id):
    """Parse a single FIT file's bytes into (session_dict, key, track_pts,
    timeseries_dict), matching the schema used in kite_data_clean.json.gz.

    Mirrors the per-session logic in extract_full.py's batch loop, adapted to
    work from in-memory bytes for one Garmin activity rather than a local
    file path, and keyed by Garmin activity ID instead of filename.
    """
    result = parse_fit(raw)
    if not result:
        return None
    sessions, records = result
    if not sessions:
        return None

    s = sessions[0]
    dist = s.get(9, 0)
    dist_km = dist / 100 / 1000 if dist and dist != INVALID32 else 0
    if dist_km < 3:
        return None

    ts = s.get(253, 0)
    if not ts or ts == INVALID32:
        return None
    ts_end = ts + FIT_EPOCH
    dur_ms = s.get(7, 0)
    dur_min = dur_ms / 1000 / 60 if dur_ms and dur_ms != INVALID32 else 0
    ts_start = ts_end - int(dur_min * 60)

    avg_spd = s.get(124) or s.get(14)
    max_spd = s.get(125) or s.get(15)
    avg_kmh = avg_spd / 1000 * 3.6 if avg_spd and avg_spd < 50000 else None
    max_kmh = max_spd / 1000 * 3.6 if max_spd and max_spd < 50000 else None
    avg_hr = v_or_none(s.get(16), 255)
    max_hr = v_or_none(s.get(17), 255)
    avg_hr = avg_hr if avg_hr and 40 < avg_hr < 250 else None
    max_hr = max_hr if max_hr and 40 < max_hr < 250 else None
    calories = v_or_none(s.get(11))
    calories = calories if calories and calories < 9999 else None

    avg_alt = to_alt(s.get(126) or s.get(44))
    min_alt = to_alt(s.get(127) or s.get(57))
    max_alt = to_alt(s.get(128) or s.get(45))
    total_asc = v_or_none(s.get(22))
    total_desc = v_or_none(s.get(23))
    avg_temp = v_or_none(s.get(94))
    avg_temp = avg_temp if avg_temp and -50 < avg_temp < 60 else None

    dt = datetime.fromtimestamp(ts_end, tz=timezone.utc)
    date_str = dt.strftime('%Y-%m-%d')
    year, month = dt.year, dt.month

    track_pts, speed_ts, hr_ts, alt_ts = [], [], [], []
    for r in records:
        r_ts = r['ts']
        if not r_ts:
            continue
        r_unix = r_ts + FIT_EPOCH
        if r_unix < ts_start - 120 or r_unix > ts_end + 120:
            continue

        lat = to_deg(r['lat'])
        lon = to_deg(r['lon'])
        if r['ealt'] is not None:
            alt_m = to_alt(r['ealt'], r['ealt_size'])
        else:
            alt_m = to_alt(r['alt'], 2)
        spd_raw = r['spd']
        spd_kmh = round(spd_raw / 1000 * 3.6, 1) if spd_raw and spd_raw < 50000 else None
        hr_val = r['hr']
        hr_ok = hr_val and 40 < hr_val < 250

        rel_min = round((r_unix - ts_start) / 60, 1)
        if rel_min < 0 or rel_min > dur_min + 10:
            continue

        if lat and lon and abs(lat) <= 85 and abs(lon) <= 179:
            track_pts.append({'lat': round(lat, 5), 'lon': round(lon, 5),
                               'spd': spd_kmh or 0, 'alt': alt_m})

        speed_ts.append([rel_min, spd_kmh])
        hr_ts.append([rel_min, hr_val if hr_ok else None])
        alt_ts.append([rel_min, alt_m])

    if track_pts:
        lats = [p['lat'] for p in track_pts]
        lons = [p['lon'] for p in track_pts]
        clat, clon = sum(lats) / len(lats), sum(lons) / len(lons)
        alts_valid = [p['alt'] for p in track_pts if p['alt'] is not None]
        if alts_valid:
            avg_alt = round(sum(alts_valid) / len(alts_valid))
            min_alt = round(min(alts_valid))
            max_alt = round(max(alts_valid))
    else:
        clat = clon = None

    location = get_location(clat, clon)
    sport_type = classify(clat, clon)

    has_hr = any(x[1] is not None for x in hr_ts)
    has_alt = any(x[1] is not None for x in alt_ts)

    if len(track_pts) > 500:
        step = len(track_pts) // 500
        track_pts = track_pts[::step]

    key = f'garmin_{activity_id}'
    session = {
        'filename': key, 'date': date_str, 'year': year, 'month': month,
        'duration_min': round(dur_min, 1),
        'distance_km': round(dist_km, 2),
        'avg_speed_kmh': round(avg_kmh, 1) if avg_kmh else None,
        'max_speed_kmh': round(max_kmh, 1) if max_kmh else None,
        'avg_hr': avg_hr, 'max_hr': max_hr, 'calories': calories,
        'avg_alt': avg_alt, 'min_alt': min_alt, 'max_alt': max_alt,
        'total_ascent': total_asc, 'total_descent': total_desc,
        'avg_temp': avg_temp,
        'location': location, 'sport_type': sport_type,
        'centroid_lat': round(clat, 4) if clat else None,
        'centroid_lon': round(clon, 4) if clon else None,
        'start_timestamp': ts_start,
        'has_hr': has_hr, 'has_alt': has_alt,
        'activity_id': activity_id,
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
    email = os.environ.get('GARMIN_EMAIL')
    password = os.environ.get('GARMIN_PASSWORD')
    if not email or not password:
        print(
            'ERROR: GARMIN_EMAIL and GARMIN_PASSWORD must be set in a local .env file.\n'
            'Copy .env.example to .env and fill in your own credentials.',
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        client = Garmin(email, password)
        client.login()
    except GarminConnectAuthenticationError as e:
        print(
            f'ERROR: Garmin login failed: {e}\n'
            'If your account has 2-step verification enabled, Garmin Connect '
            'may reject this login flow — see README.md for details.',
            file=sys.stderr,
        )
        sys.exit(1)

    print('Fetching activities from Garmin Connect...')
    activities = fetch_all_activities(client)
    print(f'Fetched {len(activities)} total activities.')

    kite_activities = [a for a in activities if is_kite_activity(a)]
    print(f'Found {len(kite_activities)} kite-related activities.')

    data = load_existing_data()
    data.setdefault('tracks', {})
    data.setdefault('timeseries', {})
    existing_ids = {s.get('activity_id') for s in data['sessions'] if s.get('activity_id')}

    added = 0
    for act in kite_activities:
        activity_id = act.get('activityId')
        if activity_id is None or activity_id in existing_ids:
            continue

        try:
            fit_bytes = download_fit_bytes(client, activity_id)
        except Exception as e:
            print(f'WARN: failed to download activity {activity_id}: {e}')
            continue

        result = process_fit_bytes(fit_bytes, activity_id)
        if not result:
            print(f'SKIP: activity {activity_id} did not parse into a valid kite '
                  'session (too short, missing GPS/timestamp, etc.)')
            continue

        session, key, track_pts, timeseries = result
        data['sessions'].append(session)
        data['tracks'][key] = track_pts
        data['timeseries'][key] = timeseries
        existing_ids.add(activity_id)
        added += 1
        print(f'Added activity {activity_id} ({session["date"]}, {session["distance_km"]} km).')

    data['sessions'].sort(key=lambda x: x['start_timestamp'])
    save_data(data)

    synced_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    with open(SYNCED_FILE, 'w') as f:
        f.write(synced_at)

    print(f'Sync complete. Added {added} new session(s). Last synced: {synced_at}')


if __name__ == '__main__':
    main()
