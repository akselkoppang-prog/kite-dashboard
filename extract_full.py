import struct, os, json
from datetime import datetime, timezone

FIT_EPOCH = 631065600
SEMICIRCLE = 180.0 / (2**31)
INVALID32 = 0x7FFFFFFF
INVALID16 = 0xFFFF
INVALID8  = 0xFF

def to_deg(v):
    if v is None or v == INVALID32: return None
    if v >= 2**31: v -= 2**32
    d = v * SEMICIRCLE
    return round(d, 6) if abs(d) < 179.9 else None

def to_alt(v, size=4):
    # FIT altitude: standard uint32 scale=5 offset=500. uint16 uses scale=20 (observed).
    if v is None: return None
    invalid = INVALID16 if size <= 2 else INVALID32
    if v == invalid: return None
    scale = 20.0 if size <= 2 else 5.0
    alt = v / scale - 500.0
    return round(alt, 1) if -200 < alt < 4500 else None

def parse_fit(data):
    if len(data) < 14 or data[8:12] != b'.FIT': return None
    hs = data[0]; ds = struct.unpack('<I', data[4:8])[0]
    pos = hs; end = min(hs + ds, len(data))
    lm = {}; sessions = []; records = []
    last_ts = 0
    while pos < end:
        if pos >= len(data): break
        hb = data[pos]
        if hb & 0x80:
            ln = (hb >> 5) & 0x03; tsoff = hb & 0x1F
            last_ts = (last_ts & 0xFFFFFFE0) | tsoff
            if tsoff < (last_ts & 0x1F): last_ts += 0x20
            pos += 1; continue
        mt = (hb >> 6) & 1; has_dev = (hb >> 5) & 1; ln = hb & 0x0F
        if mt == 1:  # definition message (bit 6 set)
            pos += 1
            if pos + 4 > len(data): break
            pos += 1; arch = data[pos]; pos += 1
            gm = struct.unpack('<H' if arch==0 else '>H', data[pos:pos+2])[0]; pos += 2
            nf = data[pos]; pos += 1; flds = []
            for _ in range(nf):
                if pos+3>len(data): break
                flds.append((data[pos], data[pos+1], data[pos+2])); pos += 3
            dev_extra = 0
            if has_dev:  # developer field definitions follow (bit 5 of header)
                if pos < len(data):
                    nd = data[pos]; pos += 1
                    for _ in range(nd):
                        if pos+3>len(data): break
                        dev_extra += data[pos+1]  # accumulate dev field sizes
                        pos += 3
            lm[ln] = (gm, flds, arch, dev_extra)
        elif mt == 0:
            pos += 1
            if ln not in lm: break
            entry = lm[ln]; gm, flds, arch = entry[0], entry[1], entry[2]
            dev_extra = entry[3] if len(entry) > 3 else 0
            row = {}
            for fn2, fs, ft in flds:
                if pos+fs>len(data): break
                rv = data[pos:pos+fs]; pos += fs
                if fs==1: v=rv[0]
                elif fs==2: v=struct.unpack('<H' if arch==0 else '>H', rv)[0]
                elif fs==4: v=struct.unpack('<I' if arch==0 else '>I', rv)[0]
                elif fs==8: v=struct.unpack('<Q' if arch==0 else '>Q', rv)[0]
                else: v=rv
                row[fn2] = v
            if dev_extra: pos += dev_extra  # skip developer field data bytes
            if gm == 18: sessions.append(row)
            elif gm == 20:
                rts = row.get(253, last_ts)
                if rts and rts != INVALID32: last_ts = rts
                # Determine field 87 size from definition
                f87_size = next((fs for fn2,fs,ft in flds if fn2==87), 4)
                records.append({
                    'ts': last_ts,
                    'lat': row.get(0), 'lon': row.get(1),
                    'alt': row.get(2),
                    'ealt': row.get(87), 'ealt_size': f87_size,
                    'spd': row.get(78) or row.get(6) or row.get(73),
                    'hr': row.get(3),
                    'temp': row.get(53),
                    'dist': row.get(5),
                })
        else: pos += 1
    return sessions, records

def is_kite(sessions):
    for s in sessions:
        sn = s.get(110, b'')
        if isinstance(sn, bytes) and b'kite' in sn.lower(): return True
        if s.get(5) == 44: return True
    return False

def get_location(lat, lon):
    if lat is None or lon is None: return 'Unknown'

    # ── Spain / Mediterranean ─────────────────────────────────────
    if 35.5 <= lat <= 44.0 and -10.0 <= lon <= 4.5:
        if 37.65 <= lat <= 37.90 and -1.05 <= lon <= -0.55:
            return 'La Manga, Spain'    # Mar Menor / Cartagena coast
        return 'Spain'

    # ── United Kingdom ────────────────────────────────────────────
    if lon < 0 and 49.5 <= lat <= 59.0:
        if 50.5 <= lat <= 51.6 and -1.5 <= lon <= 0.5:
            return 'Adur, West Sussex'   # Shoreham-by-Sea area
        return 'United Kingdom'

    # ── Denmark ───────────────────────────────────────────────────
    if lat < 57.5 and 4.0 <= lon <= 13.0:
        if 56.60 <= lat <= 56.80 and 8.00 <= lon <= 8.40:
            return 'Thyborøn, Denmark'  # Limfjord mouth
        if 56.80 <= lat <= 57.20 and 8.35 <= lon <= 8.85:
            return 'Thisted, Denmark'   # Thy / Thisted area
        return 'Denmark'

    # ── Norway – coast / fjord (kiteboarding) ─────────────────────
    if 59.08 <= lat <= 59.24 and 10.40 <= lon <= 10.60:
        return 'Vear, Tønsberg'
    if 59.24 <= lat <= 59.42 and 10.55 <= lon <= 10.85:
        return 'Rygge, Oslofjord'
    if 59.54 <= lat <= 59.70 and 10.28 <= lon <= 10.58:
        return 'Hurum, Oslofjord'

    # ── Norway – mountain / inland (snowkiting) ───────────────────
    # Hardangervidda: split west (Eidfjord) vs east (Hol/Finse)
    if 60.28 <= lat <= 60.52 and 7.45 <= lon <= 7.68:
        return 'Eidfjord, Hardangervidda'
    if 60.35 <= lat <= 60.52 and 7.68 <= lon <= 8.25:
        return 'Hol, Hardangervidda'
    if 60.28 <= lat <= 60.42 and 8.40 <= lon <= 8.62:
        return 'Nore og Uvdal'
    if 60.75 <= lat <= 61.08 and 8.55 <= lon <= 8.90:
        return 'Hemsedal / Dagali'
    # Valdres plateau: Øystre Slidre (lower) vs Vang (north of lake)
    if 61.20 <= lat <= 61.42 and 8.74 <= lon <= 8.97:
        return 'Øystre Slidre, Valdres'
    if 61.42 <= lat <= 61.65 and 8.74 <= lon <= 8.97:
        return 'Vang, Valdres'
    if 61.40 <= lat <= 61.65 and 8.10 <= lon <= 8.50:
        return 'Lom, Jotunheimen'
    if 62.50 <= lat <= 62.75 and 11.20 <= lon <= 11.65:
        return 'Røros'

    return 'Norway'

def classify(lat, lon):
    if lat is None: return 'snowkiting'
    if lon is not None and lon < 0: return 'kiteboarding'  # UK coast
    if lat < 58.0: return 'kiteboarding'                   # Denmark coast
    if 59.0 <= lat <= 60.5 and lon >= 10.0: return 'kiteboarding'  # Norway fjord/coast
    return 'snowkiting'

def csv_to_utc(s):
    dt = datetime.strptime(s.strip(), '%Y-%m-%d %H:%M:%S')
    offset = 2 if 4 <= dt.month <= 9 else 1
    return int(dt.replace(tzinfo=timezone.utc).timestamp()) - offset * 3600

import csv
csv_times = {}
with open('/sessions/vibrant-friendly-franklin/mnt/uploads/Activities.csv', newline='', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f, delimiter=','):
        dc = row.get('Dato','').strip()
        if dc:
            try: csv_times[csv_to_utc(dc)] = row
            except: pass

fit_dirs = [
    '/sessions/vibrant-friendly-franklin/mnt/UploadedFiles_0-_Part1',
    '/sessions/vibrant-friendly-franklin/mnt/UploadedFiles_0-_Part2',
    '/sessions/vibrant-friendly-franklin/mnt/UploadedFiles_0-_Part3',
    '/sessions/vibrant-friendly-franklin/mnt/UploadedFiles_0-_Part4',
    '/sessions/vibrant-friendly-franklin/mnt/uploads',
]
fit_files = []
seen = set()
for d in fit_dirs:
    if os.path.exists(d):
        for f in sorted(os.listdir(d)):
            if f.endswith('.fit') and f not in seen:
                seen.add(f); fit_files.append(os.path.join(d, f))

def downsample(lst, n=200):
    if len(lst) <= n: return lst
    step = max(1, len(lst)//n)
    return lst[::step]

def v_or_none(v, invalid=INVALID32):
    return None if (v is None or v == invalid or v == INVALID16 or v == INVALID8) else v

sessions_out = []; tracks_out = {}; timeseries_out = {}
skipped_csv = 0

for fp in fit_files:
    with open(fp, 'rb') as f: raw = f.read()
    if b'kite' not in raw.lower() and b'thesurfrapp' not in raw.lower(): continue
    result = parse_fit(raw)
    if not result: continue
    sessions, records = result
    if not is_kite(sessions): continue

    for s in sessions:
        dist = s.get(9, 0)
        dist_km = dist / 100 / 1000 if dist and dist != INVALID32 else 0
        if dist_km < 3: continue

        ts = s.get(253, 0)
        if not ts or ts == INVALID32: continue
        ts_end = ts + FIT_EPOCH
        dur_ms = s.get(7, 0)
        dur_min = dur_ms / 1000 / 60 if dur_ms and dur_ms != INVALID32 else 0
        ts_start = ts_end - int(dur_min * 60)

        # CSV match using start time ±3h
        best_csv = None; best_diff = 9999999
        for csv_ts, csv_row in csv_times.items():
            diff = abs(csv_ts - ts_start)
            if diff < 10800 and diff < best_diff:
                best_diff = diff; best_csv = csv_row
        if not best_csv: skipped_csv += 1  # allow sessions without CSV match

        # Session stats
        avg_spd = s.get(124) or s.get(14)
        max_spd = s.get(125) or s.get(15)
        avg_kmh = avg_spd / 1000 * 3.6 if avg_spd and avg_spd < 50000 else None
        max_kmh = max_spd / 1000 * 3.6 if max_spd and max_spd < 50000 else None
        avg_hr = v_or_none(s.get(16), 255); max_hr = v_or_none(s.get(17), 255)
        avg_hr = avg_hr if avg_hr and 40 < avg_hr < 250 else None
        max_hr = max_hr if max_hr and 40 < max_hr < 250 else None
        calories = v_or_none(s.get(11)); calories = calories if calories and calories < 9999 else None

        # Elevation stats from session
        # Enhanced altitude fields (126=avg, 127=min, 128=max)
        avg_alt = to_alt(s.get(126) or s.get(44))
        min_alt = to_alt(s.get(127) or s.get(57))
        max_alt = to_alt(s.get(128) or s.get(45))
        total_asc = v_or_none(s.get(22)); total_desc = v_or_none(s.get(23))
        avg_temp = v_or_none(s.get(94)); avg_temp = avg_temp if avg_temp and -50 < avg_temp < 60 else None

        dt = datetime.fromtimestamp(ts_end, tz=timezone.utc)
        date_str = dt.strftime('%Y-%m-%d'); year = dt.year; month = dt.month

        # Build GPS track + time series from records
        track_pts = []; speed_ts = []; hr_ts = []; alt_ts = []
        prev_dist = 0

        for r in records:
            r_ts = r['ts']
            if not r_ts: continue
            r_unix = r_ts + FIT_EPOCH
            if r_unix < ts_start - 120 or r_unix > ts_end + 120: continue

            lat = to_deg(r['lat']); lon = to_deg(r['lon'])
            # Use enhanced_altitude (field 87) with correct size-aware scale, fallback to field 2
            if r['ealt'] is not None:
                alt_m = to_alt(r['ealt'], r['ealt_size'])
            else:
                alt_m = to_alt(r['alt'], 2)
            spd_raw = r['spd']
            spd_kmh = round(spd_raw / 1000 * 3.6, 1) if spd_raw and spd_raw < 50000 else None
            hr_val = r['hr']; hr_ok = hr_val and 40 < hr_val < 250
            temp = r['temp']

            rel_min = round((r_unix - ts_start) / 60, 1)
            if rel_min < 0 or rel_min > dur_min + 10: continue

            if lat and lon and abs(lat) <= 85 and abs(lon) <= 179:
                track_pts.append({'lat': round(lat,5), 'lon': round(lon,5),
                                   'spd': spd_kmh or 0, 'alt': alt_m})

            speed_ts.append([rel_min, spd_kmh])
            hr_ts.append([rel_min, hr_val if hr_ok else None])
            alt_ts.append([rel_min, alt_m])

        # Fix 3 known files that have GPS but timestamp doesn't match — use all records
        WIDE_WINDOW_FILES = {
            'aksel.koppang@hotmail.com_99602456246.fit',
            'aksel.koppang@hotmail.com_126298517569.fit',
            'aksel.koppang@hotmail.com_157021654664.fit',
        }
        if not track_pts and os.path.basename(fp) in WIDE_WINDOW_FILES:
            for r in records:
                lat = to_deg(r['lat']); lon = to_deg(r['lon'])
                if r['ealt'] is not None:
                    alt_m = to_alt(r['ealt'], r['ealt_size'])
                else:
                    alt_m = to_alt(r['alt'], 2)
                spd_raw = r['spd']
                spd_kmh = round(spd_raw/1000*3.6,1) if spd_raw and spd_raw < 50000 else None
                hr_val = r['hr']; hr_ok = hr_val and 40 < hr_val < 250
                r_unix = r['ts'] + FIT_EPOCH
                rel_min = round((r_unix - ts_start) / 60, 1)
                if lat and lon and abs(lat) <= 85 and abs(lon) <= 179:
                    track_pts.append({'lat': round(lat,5), 'lon': round(lon,5), 'spd': spd_kmh or 0, 'alt': alt_m})
                if 0 <= rel_min <= dur_min + 10:
                    speed_ts.append([rel_min, spd_kmh])
                    hr_ts.append([rel_min, hr_val if hr_ok else None])
                    alt_ts.append([rel_min, alt_m])

        if track_pts:
            lats = [p['lat'] for p in track_pts]; lons = [p['lon'] for p in track_pts]
            clat = sum(lats)/len(lats); clon = sum(lons)/len(lons)
            # Fill alt stats from records
            alts_valid = [p['alt'] for p in track_pts if p['alt'] is not None]
            if alts_valid:
                avg_alt = round(sum(alts_valid)/len(alts_valid))
                min_alt = round(min(alts_valid))
                max_alt = round(max(alts_valid))
            else:
                avg_alt = min_alt = max_alt = None
        else:
            clat = clon = None; avg_alt = min_alt = max_alt = None

        location = get_location(clat, clon)
        sport_type = classify(clat, clon)
        fn = os.path.basename(fp)

        has_hr = any(x[1] is not None for x in hr_ts)
        has_alt = any(x[1] is not None for x in alt_ts)

        # Downsample tracks
        if len(track_pts) > 500:
            step = len(track_pts)//500
            track_pts = track_pts[::step]

        sessions_out.append({
            'filename': fn, 'date': date_str, 'year': year, 'month': month,
            'duration_min': round(dur_min,1),
            'distance_km': round(dist_km,2),
            'avg_speed_kmh': round(avg_kmh,1) if avg_kmh else None,
            'max_speed_kmh': round(max_kmh,1) if max_kmh else None,
            'avg_hr': avg_hr, 'max_hr': max_hr, 'calories': calories,
            'avg_alt': avg_alt, 'min_alt': min_alt, 'max_alt': max_alt,
            'total_ascent': total_asc, 'total_descent': total_desc,
            'avg_temp': avg_temp,
            'location': location, 'sport_type': sport_type,
            'centroid_lat': round(clat,4) if clat else None,
            'centroid_lon': round(clon,4) if clon else None,
            'start_timestamp': ts_start,
            'has_hr': has_hr, 'has_alt': has_alt,
        })
        tracks_out[fn] = track_pts
        timeseries_out[fn] = {
            'speed': downsample(speed_ts),
            'hr': downsample(hr_ts) if has_hr else [],
            'alt': downsample(alt_ts) if has_alt else [],
        }

# Deduplicate by start_timestamp — prefer hash-named files (already processed first from Part dirs)
seen_ts = {}
deduped = []
for s in sessions_out:
    ts = s['start_timestamp']
    if ts not in seen_ts:
        seen_ts[ts] = True
        deduped.append(s)
sessions_out = sorted(deduped, key=lambda x: x['start_timestamp'])

print(f"Sessions: {len(sessions_out)}, skipped_csv: {skipped_csv}")
print(f"With altitude: {sum(1 for s in sessions_out if s['has_alt']}")
print(f"With HR: {sum(1 for s in sessions_out if s['has_hr'])}")
print(f"Locations: {sorted(set(s['location'] for s in sessions_out))}")
# Sample alt stats
for s in sessions_out[:3]:
    print(f"  {s['date']} alt={s['avg_alt']} min={s['min_alt']} max={s['max_alt']} asc={s['total_ascent']}")

out = {'ressions': sessions_out, 'tracks': tracks_out, 'timeseries': timeseries_out}
with open('/sessions/vibrant-friendly-franklin/kite_data_clean.json','w') as f:
    json.dump(out, f)
print("Saved")
