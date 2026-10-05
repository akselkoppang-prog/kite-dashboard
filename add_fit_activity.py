"""
Manually add a single Garmin FIT activity file to kite_data_clean.json.gz.

A lightweight alternative to Strava sync (which requires a paid Strava API
subscription) — download the .fit file for an activity from Garmin Connect
(Activity -> ⚙️ gear icon -> Export Original) and run:

    python add_fit_activity.py path/to/ACTIVITY.fit

Reuses the same parsing/classification logic as extract_full.py so sessions
added this way match the existing dataset's schema exactly.
"""
import sys
import os
import gzip
import json
from datetime import datetime, timezone

from extract_full import (
    parse_fit, is_kite, get_location, classify, to_alt, to_deg,
    downsample, v_or_none, FIT_EPOCH, INVALID32,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'kite_data_clean.json.gz')


def load_existing_data():
    if os.path.exists(DATA_FILE):
        with gzip.open(DATA_FILE, 'rt', encoding='utf-8') as f:
            return json.load(f)
    return {'sessions': [], 'tracks': {}, 'timeseries': {}}


def save_data(data):
    with gzip.open(DATA_FILE, 'wt', encoding='utf-8') as f:
        json.dump(data, f)


def process_fit(fp, force=False, strip_alt=False):
    """Mirrors the per-session extraction logic in extract_full.py's
    __main__ batch loop, but for a single file.

    force=True skips the kite-name/sport-type check — useful for sessions
    recorded in a fallback sport mode (e.g. "Run") because the device's
    kite sport mode didn't work.

    strip_alt=True discards altitude/ascent data — useful when a fallback
    sport mode left the barometric altimeter uncalibrated, producing
    physically-impossible elevation swings."""
    with open(fp, 'rb') as f:
        raw = f.read()
    result = parse_fit(raw)
    if not result:
        return []
    sessions, records = result
    if not force and not is_kite(sessions) and b'kite' not in raw.lower() and b'thesurfrapp' not in raw.lower():
        return []

    out = []
    for s in sessions:
        dist = s.get(9, 0)
        dist_km = dist / 100 / 1000 if dist and dist != INVALID32 else 0
        if dist_km < 3:
            continue

        ts = s.get(253, 0)
        if not ts or ts == INVALID32:
            continue
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

        clat = clon = None
        if track_pts:
            lats = [p['lat'] for p in track_pts]
            lons = [p['lon'] for p in track_pts]
            clat, clon = sum(lats) / len(lats), sum(lons) / len(lons)
            alts_valid = [p['alt'] for p in track_pts if p['alt'] is not None]
            if alts_valid:
                avg_alt = round(sum(alts_valid) / len(alts_valid))
                min_alt = round(min(alts_valid))
                max_alt = round(max(alts_valid))

        location = get_location(clat, clon)
        sport_type = classify(clat, clon)
        fn = os.path.basename(fp)

        has_hr = any(x[1] is not None for x in hr_ts)
        has_alt = any(x[1] is not None for x in alt_ts)

        if len(track_pts) > 500:
            step = len(track_pts) // 500
            track_pts = track_pts[::step]

        session = {
            'filename': fn, 'date': date_str, 'year': year, 'month': month,
            'duration_min': round(dur_min, 1),
            'distance_km': round(dist_km, 2),
            'avg_speed_kmh': round(avg_kmh, 1) if avg_kmh else None,
            'max_speed_kmh': round(max_kmh, 1) if max_kmh else None,
            'avg_hr': avg_hr, 'max_hr': max_hr, 'calories': calories,
            'avg_alt': None if strip_alt else avg_alt,
            'min_alt': None if strip_alt else min_alt,
            'max_alt': None if strip_alt else max_alt,
            'total_ascent': None if strip_alt else total_asc,
            'total_descent': None if strip_alt else total_desc,
            'avg_temp': avg_temp,
            'location': location, 'sport_type': sport_type,
            'centroid_lat': round(clat, 4) if clat is not None else None,
            'centroid_lon': round(clon, 4) if clon is not None else None,
            'start_timestamp': ts_start,
            'has_hr': has_hr, 'has_alt': False if strip_alt else has_alt,
        }
        if strip_alt:
            for p in track_pts:
                p['alt'] = None
        timeseries = {
            'speed': downsample(speed_ts),
            'hr': downsample(hr_ts) if has_hr else [],
            'alt': [] if strip_alt else (downsample(alt_ts) if has_alt else []),
        }
        out.append((session, fn, track_pts, timeseries))
    return out


def main():
    args = sys.argv[1:]
    force = '--force' in args
    strip_alt = '--no-alt' in args
    overwrite = '--overwrite' in args
    args = [a for a in args if a not in ('--force', '--no-alt', '--overwrite')]
    if len(args) != 1:
        print('Usage: python add_fit_activity.py [--force] [--no-alt] [--overwrite] path/to/ACTIVITY.fit', file=sys.stderr)
        print('  --force      add even if not detected as a kite session (e.g. recorded', file=sys.stderr)
        print('               in a fallback sport mode like "Run")', file=sys.stderr)
        print('  --no-alt     discard altitude/ascent data (e.g. uncalibrated barometer', file=sys.stderr)
        print('               in a fallback sport mode)', file=sys.stderr)
        print('  --overwrite  replace an already-added session with the same start time', file=sys.stderr)
        sys.exit(1)
    fp = args[0]
    if not os.path.exists(fp):
        print(f'ERROR: file not found: {fp}', file=sys.stderr)
        sys.exit(1)

    results = process_fit(fp, force=force, strip_alt=strip_alt)
    if not results:
        print('No kite activity found in this file (not kite-tagged, or under 3km). '
              'Use --force to add anyway.')
        sys.exit(0)

    data = load_existing_data()
    data.setdefault('tracks', {})
    data.setdefault('timeseries', {})
    existing_ts = {s['start_timestamp']: s for s in data['sessions']}

    added = 0
    for session, key, track_pts, timeseries in results:
        if session['start_timestamp'] in existing_ts:
            if not overwrite:
                print(f"SKIP: session at {session['date']} already exists. Use --overwrite to replace it.")
                continue
            data['sessions'] = [s for s in data['sessions']
                                 if s['start_timestamp'] != session['start_timestamp']]
            print(f"Overwriting existing session at {session['date']}.")
        data['sessions'].append(session)
        data['tracks'][key] = track_pts
        data['timeseries'][key] = timeseries
        existing_ts[session['start_timestamp']] = session
        added += 1

    data['sessions'].sort(key=lambda x: x['start_timestamp'])
    save_data(data)
    print(f'Added {added} session(s) from {os.path.basename(fp)}.')


if __name__ == '__main__':
    main()
