import json, gzip, os

_data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kite_data_clean.json.gz')
with gzip.open(_data_file, 'rt', encoding='utf-8') as f:
    kite_data = json.load(f)

sessions_json = json.dumps(kite_data['sessions'])
tracks_json = json.dumps(kite_data['tracks'])
timeseries_json = json.dumps(kite_data.get('timeseries', {}))

html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kite Dashboard — Aksel</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css"/>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Sortable/1.15.0/Sortable.min.js"></script>
<style>
  :root {
    --bg: #0a0e1a;
    --surface: #111827;
    --surface2: #1a2236;
    --surface3: #1e293b;
    --accent: #06b6d4;
    --accent2: #0ea5e9;
    --accent3: #38bdf8;
    --green: #10b981;
    --orange: #f59e0b;
    --red: #ef4444;
    --purple: #8b5cf6;
    --text: #e2e8f0;
    --text2: #94a3b8;
    --text3: #64748b;
    --border: #1e293b;
    --radius: 12px;
    --shadow: 0 4px 20px rgba(0,0,0,0.4);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }

  /* Header */
  .header { 
    background: linear-gradient(135deg, #0a1628 0%, #0d2040 50%, #0a1628 100%);
    border-bottom: 1px solid var(--border);
    padding: 20px 24px;
    display: flex; align-items: center; gap: 16px;
    position: sticky; top: 0; z-index: 100;
    backdrop-filter: blur(10px);
  }
  .header-icon { font-size: 2rem; }
  .header-title { flex: 1; }
  .header-title h1 { font-size: 1.4rem; font-weight: 700; background: linear-gradient(90deg, var(--accent3), var(--accent)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .header-title p { color: var(--text2); font-size: 0.82rem; margin-top: 2px; }
  
  /* Filters */
  .filter-bar {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 12px 24px;
    display: flex; gap: 12px; align-items: center; flex-wrap: wrap;
  }
  .filter-label { color: var(--text2); font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
  .filter-btn {
    padding: 5px 14px; border-radius: 20px; border: 1px solid var(--border);
    background: var(--surface2); color: var(--text2); cursor: pointer; font-size: 0.82rem;
    transition: all 0.15s;
  }
  .filter-btn:hover { border-color: var(--accent); color: var(--accent); }
  .filter-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); font-weight: 600; }
  .filter-sep { width: 1px; height: 20px; background: var(--border); margin: 0 4px; }

  /* Main layout */
  .main { padding: 20px 24px; max-width: 1800px; margin: 0 auto; }
  
  /* Stats row */
  .stats-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; margin-bottom: 20px; }
  .stat-card {
    background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
    padding: 18px 20px; position: relative; overflow: hidden;
    transition: transform 0.15s, border-color 0.15s;
  }
  .stat-card:hover { transform: translateY(-2px); border-color: var(--accent); }
  .stat-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; }
  .stat-card.teal::before { background: linear-gradient(90deg, var(--accent), var(--accent2)); }
  .stat-card.green::before { background: linear-gradient(90deg, var(--green), #34d399); }
  .stat-card.orange::before { background: linear-gradient(90deg, var(--orange), #fbbf24); }
  .stat-card.purple::before { background: linear-gradient(90deg, var(--purple), #a78bfa); }
  .stat-card.red::before { background: linear-gradient(90deg, var(--red), #f87171); }
  .stat-card.blue::before { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
  .stat-label { font-size: 0.75rem; color: var(--text3); text-transform: uppercase; letter-spacing: 0.06em; font-weight: 600; }
  .stat-value { font-size: 2rem; font-weight: 800; margin-top: 6px; line-height: 1; }
  .stat-value.teal { color: var(--accent3); }
  .stat-value.green { color: var(--green); }
  .stat-value.orange { color: var(--orange); }
  .stat-value.purple { color: var(--purple); }
  .stat-value.red { color: var(--red); }
  .stat-value.blue { color: #60a5fa; }
  .stat-unit { font-size: 0.85rem; color: var(--text2); margin-top: 4px; }

  /* Chart grid */
  .chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
  .chart-grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-bottom: 20px; }
  .chart-card {
    background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
    padding: 20px; position: relative;
  }
  .chart-card.full { grid-column: 1 / -1; }
  .chart-card.two-thirds { grid-column: span 2; }
  .card-title {
    font-size: 0.85rem; font-weight: 700; color: var(--text2); text-transform: uppercase;
    letter-spacing: 0.06em; margin-bottom: 14px; display: flex; align-items: center; gap: 8px;
  }
  .card-title .dot { width: 8px; height: 8px; border-radius: 50%; }
  .chart-container { position: relative; }

  /* Map */
  #map { height: 420px; border-radius: 8px; }
  .leaflet-container { background: #0a1628 !important; }
  /* ESRI dark gray tiles work from file:// with no API key */

  /* Calendar heatmap */
  .cal-grid { display: flex; flex-direction: column; gap: 3px; }
  .cal-row { display: flex; gap: 3px; align-items: center; }
  .cal-month-label { font-size: 0.65rem; color: var(--text3); width: 24px; flex-shrink: 0; }
  .cal-cell {
    width: 14px; height: 14px; border-radius: 3px;
    background: var(--surface3); cursor: pointer;
    transition: transform 0.1s;
    position: relative;
  }
  .cal-cell:hover { transform: scale(1.4); z-index: 10; }
  .cal-cell.level-1 { background: #0c4a2c; }
  .cal-cell.level-2 { background: #166534; }
  .cal-cell.level-3 { background: #16a34a; }
  .cal-cell.level-4 { background: #22c55e; }
  .cal-day-label { font-size: 0.6rem; color: var(--text3); text-align: right; width: 24px; }

  /* Table */
  .table-wrap { overflow-x: auto; border-radius: 8px; }
  table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
  thead { background: var(--surface2); position: sticky; top: 0; z-index: 5; }
  th {
    padding: 10px 14px; text-align: left; font-size: 0.72rem; text-transform: uppercase;
    letter-spacing: 0.07em; color: var(--text3); font-weight: 700; cursor: pointer;
    white-space: nowrap; user-select: none;
  }
  th:hover { color: var(--accent); }
  th.sorted { color: var(--accent3); }
  th .sort-arrow { margin-left: 4px; }
  td { padding: 9px 14px; border-bottom: 1px solid rgba(30,41,59,0.8); white-space: nowrap; }
  tr:hover td { background: var(--surface2); }
  tr.selected td { background: rgba(6,182,212,0.08); }
  tr.selected td:first-child { border-left: 3px solid var(--accent); }
  .badge {
    display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 600;
  }
  .speed-bar { 
    display: inline-block; height: 6px; border-radius: 3px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    vertical-align: middle; margin-right: 6px;
  }

  /* Tooltip */
  .tooltip { 
    position: absolute; background: rgba(17,24,39,0.95); border: 1px solid var(--border);
    padding: 8px 12px; border-radius: 8px; font-size: 0.78rem; pointer-events: none;
    display: none; z-index: 200; backdrop-filter: blur(10px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
  }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: var(--bg); }
  ::-webkit-scrollbar-thumb { background: var(--surface3); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--text3); }

  /* Responsive */
  @media (max-width: 900px) {
    .chart-grid, .chart-grid-3 { grid-template-columns: 1fr; }
    .chart-card.two-thirds { grid-column: 1; }
  }
  
  /* Speed gradient legend */
  .legend { display: flex; align-items: center; gap: 8px; font-size: 0.72rem; color: var(--text3); }
  .legend-gradient { width: 80px; height: 8px; border-radius: 4px; background: linear-gradient(90deg, #06b6d4, #0ea5e9, #f59e0b, #ef4444); }

  /* ============ DETAIL PANEL ============ */
  .detail-panel {
    position: fixed; top: 0; right: 0; width: 540px; height: 100vh;
    background: #07101f; border-left: 1px solid #1e293b;
    z-index: 1000; transform: translateX(100%);
    transition: transform 0.32s cubic-bezier(.4,0,.2,1);
    display: flex; flex-direction: column; overflow: hidden;
    box-shadow: -16px 0 80px rgba(0,0,0,0.8);
  }
  .detail-panel.open { transform: translateX(0); }
  @keyframes dp-marker-pulse {
    0%   { r: 7; opacity: 1; }
    70%  { r: 13; opacity: 0; }
    100% { r: 7; opacity: 0; }
  }
  .dp-hover-marker { animation: dp-marker-pulse 1.2s ease-out infinite; }
  .detail-panel-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.45);
    z-index: 999; opacity: 0; pointer-events: none;
    transition: opacity 0.3s; backdrop-filter: blur(2px);
  }
  .detail-panel-overlay.open { opacity: 1; pointer-events: auto; }

  /* DP Header */
  .dp-header {
    padding: 0; flex-shrink: 0; position: relative;
    background: linear-gradient(160deg, #0d1f3c 0%, #0a1528 100%);
    border-bottom: 1px solid #1e293b;
  }
  .dp-header-banner {
    height: 6px; width: 100%;
  }
  .dp-header-content { padding: 16px 20px 18px; }
  .dp-header-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
  .dp-location { font-size: 0.72rem; color: var(--text3); font-weight: 600; text-transform: uppercase; letter-spacing:.07em; margin-bottom: 4px; display: flex; align-items: center; gap: 5px; }
  .dp-title { font-size: 1.25rem; font-weight: 800; color: var(--text); margin-bottom: 6px; }
  .dp-tags { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .dp-tag { padding: 3px 10px; border-radius: 20px; font-size: 0.73rem; font-weight: 700; background: #1e293b; color: #94a3b8; }
  .dp-close {
    width: 32px; height: 32px; border-radius: 50%; border: 1px solid #2d3748;
    background: #1a2236; color: var(--text2); cursor: pointer; font-size: 1rem;
    display: flex; align-items: center; justify-content: center; flex-shrink: 0;
    transition: all 0.15s; margin-top: -2px;
  }
  .dp-close:hover { background: #ef4444; color: #fff; border-color: #ef4444; }

  /* DP Body */
  .dp-body { flex: 1; overflow-y: auto; padding: 0 20px 28px; scroll-behavior: smooth; }
  .dp-body::-webkit-scrollbar { width: 4px; }
  .dp-body::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }

  /* Primary stats */
  .dp-primary-stats {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 0; margin: 0 -20px; border-bottom: 1px solid #1e293b;
  }
  .dp-primary-stat {
    padding: 14px 0 12px; text-align: center; border-right: 1px solid #1e293b; position: relative;
  }
  .dp-primary-stat:last-child { border-right: none; }
  .dp-primary-stat-val { font-size: 1.5rem; font-weight: 800; line-height: 1; margin-bottom: 3px; }
  .dp-primary-stat-unit { font-size: 0.65rem; color: var(--text3); text-transform: uppercase; letter-spacing:.06em; font-weight: 600; }
  .dp-primary-stat-label { font-size: 0.65rem; color: var(--text3); margin-top: 1px; }

  /* Secondary stats grid */
  .dp-secondary-stats { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; padding: 14px 0; }
  .dp-sec-stat {
    background: #0d1527; border: 1px solid #1e293b; border-radius: 8px; padding: 10px 12px;
  }
  .dp-sec-label { font-size: 0.63rem; color: var(--text3); text-transform: uppercase; letter-spacing:.06em; font-weight: 600; }
  .dp-sec-val { font-size: 1.05rem; font-weight: 700; color: var(--text); margin-top: 3px; }

  /* Section headers */
  .dp-section {
    font-size: 0.68rem; text-transform: uppercase; letter-spacing: .09em;
    color: var(--text3); font-weight: 700; margin: 16px 0 8px;
    display: flex; align-items: center; gap: 8px;
  }
  .dp-section::after { content: ''; flex: 1; height: 1px; background: #1e293b; }

  /* Charts */
  .dp-chart-box { background: #0a1628; border: 1px solid #1e293b; border-radius: 10px; padding: 14px 14px 10px; margin-bottom: 10px; }
  .dp-chart-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
  .dp-chart-label { font-size: 0.68rem; color: var(--text3); font-weight: 700; text-transform: uppercase; letter-spacing:.07em; }
  .dp-chart-hint { font-size: 0.63rem; color: #334155; font-style: italic; }
  .dp-chart-wrap { position: relative; height: 120px; cursor: crosshair; }
  .dp-no-data {
    color: var(--text3); font-size: 0.76rem; text-align: center; padding: 22px 0;
    border: 1px dashed #1e293b; border-radius: 8px;
  }

  /* Map */
  .dp-map-wrap { height: 220px; border-radius: 10px; overflow: hidden; margin-bottom: 10px; border: 1px solid #1e293b; }

  /* Comparison rows */
  .dp-comparison { display: flex; flex-direction: column; gap: 6px; }
  .dp-cmp-row { display: flex; align-items: center; gap: 10px; background: #0d1527; border-radius: 8px; padding: 9px 12px; border: 1px solid #1e293b; }
  .dp-cmp-label { font-size: 0.75rem; color: var(--text2); flex: 1; }
  .dp-cmp-bar-wrap { width: 80px; height: 5px; background: #1e293b; border-radius: 3px; overflow: hidden; }
  .dp-cmp-bar { height: 100%; border-radius: 3px; }
  .dp-cmp-val { font-size: 0.78rem; font-weight: 700; color: var(--text); min-width: 60px; text-align: right; }
  .dp-cmp-badge { font-size: 0.6rem; padding: 2px 6px; border-radius: 3px; font-weight: 700; white-space: nowrap; }

  /* Pace bar */
  .dp-pace-section { padding: 10px 0; }
  .dp-pace-row { display: flex; justify-content: space-between; font-size: 0.78rem; margin-bottom: 5px; color: var(--text2); }
  .dp-pace-bar { height: 8px; border-radius: 4px; margin-bottom: 3px; position: relative; overflow: visible; }
  .dp-pace-marker { position: absolute; top: -3px; width: 3px; height: 14px; background: white; border-radius: 2px; transform: translateX(-50%); box-shadow: 0 0 4px rgba(255,255,255,0.5); }

  /* ── Calendar Heatmap ── */
  .cal-cell { width: 13px; height: 13px; border-radius: 2px; background: #1a2236; cursor: pointer; transition: transform 0.1s, opacity 0.1s; flex-shrink: 0; }
  .cal-cell:hover { transform: scale(1.5); z-index: 10; opacity: 0.9; }
  .cal-cell.level-0 { background: #1a2236; }
  .cal-cell.level-1 { background: #0c4a3c; }
  .cal-cell.level-2 { background: #0e7050; }
  .cal-cell.level-3 { background: #10b981; }
  .cal-cell.level-4 { background: #34d399; }
  .cal-cell.kite-1  { background: #0c3a4a; }
  .cal-cell.kite-2  { background: #0e5f7a; }
  .cal-cell.kite-3  { background: #0891b2; }
  .cal-cell.kite-4  { background: #22d3ee; }
  .cal-cell.snow-1  { background: #2d1a4a; }
  .cal-cell.snow-2  { background: #4c1d95; }
  .cal-cell.snow-3  { background: #7c3aed; }
  .cal-cell.snow-4  { background: #a78bfa; }

  /* ── Speed zone pills ── */
  .zone-pill { display:inline-flex;align-items:center;gap:5px;padding:4px 10px;border-radius:10px;font-size:0.73rem;font-weight:700; }

  /* ── Radar chart in detail panel ── */
  .dp-radar-wrap { position:relative; height:200px; }

  /* ── Section headings ── */
  .dash-section-hdr {
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: .08em;
    color: var(--text3); font-weight: 700; margin: 20px 0 12px;
    display: flex; align-items: center; gap: 10px;
  }
  .dash-section-hdr::after { content:''; flex:1; height:1px; background:var(--border); }

  /* ── PB star marker (speed chart) ── */
  .pb-label { font-size: 0.6rem; color: #f59e0b; }

  /* ── Draggable widget sections ── */
  .sortable-item { margin-bottom: 16px; position: relative; }
  .sortable-item.sortable-ghost { opacity: 0.35; }
  .sortable-item.sortable-chosen > .chart-card,
  .sortable-item.sortable-chosen > .chart-grid,
  .sortable-item.sortable-chosen > .chart-grid-3 { box-shadow: 0 0 0 2px var(--accent), 0 8px 40px rgba(6,182,212,0.2); }
  .widget-drag-handle {
    position: absolute; top: 15px; right: 14px; z-index: 20;
    cursor: grab; color: #1e293b; font-size: 1.1rem; line-height: 1;
    transition: color 0.15s; user-select: none; letter-spacing: -1px;
  }
  .sortable-item:hover .widget-drag-handle { color: #475569; }
  .widget-drag-handle:hover { color: #94a3b8 !important; }
  .widget-drag-handle:active { cursor: grabbing; }
  /* multi-card rows need the handle on the wrapper */
  .widget-row-handle {
    display: flex; align-items: center; gap: 8px;
    margin-bottom: 8px; padding: 0 4px;
  }
  .widget-row-handle .row-label { font-size: 0.63rem; color: #334155; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; }
  .widget-row-handle .row-drag { cursor: grab; color: #334155; font-size: 1rem; margin-left: auto; user-select: none; transition: color 0.15s; }
  .sortable-item:hover .row-drag { color: #475569; }
  .row-drag:hover { color: #94a3b8 !important; }

  /* ── Calendar: collapsible years ── */
  .cal-year-header {
    display: flex; align-items: center; gap: 10px;
    padding: 7px 12px; border-radius: 8px; cursor: pointer;
    background: #0d1527; border: 1px solid #1e293b;
    margin-bottom: 3px; transition: background 0.15s, border-color 0.15s;
    user-select: none;
  }
  .cal-year-header:hover { background: #141f35; border-color: #2d3f5c; }
  .cal-year-label { font-size: 0.82rem; font-weight: 800; color: #94a3b8; min-width: 38px; }
  .cal-month-bar { display: flex; gap: 2px; flex: 1; align-items: center; }
  .cal-mo-block { flex: 1; height: 16px; border-radius: 3px; max-width: 24px; min-width: 8px; }
  .cal-year-meta { font-size: 0.7rem; color: #475569; white-space: nowrap; text-align: right; }
  .cal-year-chevron { font-size: 0.65rem; color: #334155; width: 14px; text-align: center; transition: transform 0.25s; }
  .cal-year-chevron.open { transform: rotate(90deg); }
  .cal-year-grid {
    max-height: 0; overflow: hidden;
    transition: max-height 0.38s cubic-bezier(0.4,0,0.2,1), opacity 0.3s;
    opacity: 0;
  }
  .cal-year-grid.open { max-height: 260px; opacity: 1; }
  .cal-year-grid-inner { padding: 8px 0 10px 4px; overflow-x: auto; }

  /* ── Personal Records ── */
  .pr-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 10px; }
  .pr-card {
    background: #0a1421; border: 1px solid #1e293b; border-radius: 10px;
    padding: 13px 16px; cursor: pointer; transition: border-color 0.15s, transform 0.12s;
    position: relative; overflow: hidden;
  }
  .pr-card:hover { border-color: #334155; transform: translateY(-2px); }
  .pr-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; }
  .pr-card-icon { font-size: 0.75rem; margin-bottom: 5px; }
  .pr-card-label { font-size: 0.62rem; color: #475569; text-transform: uppercase; letter-spacing: .07em; font-weight: 700; }
  .pr-card-val { font-size: 1.4rem; font-weight: 800; line-height: 1.1; margin-top: 4px; }
  .pr-card-sub { font-size: 0.72rem; color: #475569; margin-top: 3px; }
  .pr-card-name { font-size: 0.72rem; color: #64748b; margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
</style>
</head>
<body>

<div class="header">
  <div class="header-icon">🪁</div>
  <div class="header-title">
    <h1>Kite Dashboard</h1>
    <p id="header-subtitle">Loading data…</p>
  </div>
  <div style="display:flex;gap:8px;align-items:center;">
    <span style="font-size:0.78rem;color:var(--text3);">Last session:</span>
    <span id="last-session-date" style="font-size:0.85rem;color:var(--accent3);font-weight:600;"></span>
  </div>
</div>

<div class="filter-bar">
  <span class="filter-label">Sport</span>
  <button class="filter-btn active" data-sport="all">All</button>
  <button class="filter-btn" data-sport="kiteboarding" style="border-color:#06b6d4;">🏄 Kiteboarding</button>
  <button class="filter-btn" data-sport="snowkiting" style="border-color:#8b5cf6;">🎿 Snowkiting</button>
  <div class="filter-sep"></div>
  <span class="filter-label">Year</span>
  <button class="filter-btn active" data-year="all">All</button>
  <div id="year-filters" style="display:flex;gap:8px;"></div>
  <div class="filter-sep"></div>
  <span class="filter-label">Location</span>
  <div id="loc-filters" style="display:flex;gap:8px;flex-wrap:wrap;"></div>
  <button id="reset-filters-btn" onclick="resetAllFilters()" style="display:none;margin-left:auto;align-items:center;gap:6px;padding:5px 14px;border-radius:20px;border:1px solid #ef444466;background:#ef444411;color:#f87171;font-size:0.75rem;font-weight:700;cursor:pointer;transition:all 0.15s;white-space:nowrap;" onmouseover="this.style.background='#ef444422'" onmouseout="this.style.background='#ef444411'">✕ Reset filters</button>
</div>

<div class="main">
  <!-- ── Stats + Sport split (pinned, not sortable) ── -->
  <div class="stats-row" id="stats-row">
    <div class="stat-card teal">
      <div class="stat-label">Sessions</div>
      <div class="stat-value teal" id="stat-sessions">—</div>
      <div class="stat-unit">kite sessions</div>
    </div>
    <div class="stat-card green">
      <div class="stat-label">Total Time</div>
      <div class="stat-value green" id="stat-hours">—</div>
      <div class="stat-unit" id="stat-hours-unit">hours total</div>
    </div>
    <div class="stat-card orange">
      <div class="stat-label">Total Distance</div>
      <div class="stat-value orange" id="stat-distance">—</div>
      <div class="stat-unit">km covered</div>
    </div>
    <div class="stat-card red">
      <div class="stat-label">Max Speed</div>
      <div class="stat-value red" id="stat-maxspeed">—</div>
      <div class="stat-unit">km/h personal best</div>
    </div>
    <div class="stat-card purple">
      <div class="stat-label">Avg Moving Speed</div>
      <div class="stat-value purple" id="stat-avgspeed">—</div>
      <div class="stat-unit">km/h across all sessions</div>
    </div>
    <div class="stat-card blue">
      <div class="stat-label">Avg Session</div>
      <div class="stat-value blue" id="stat-avgsession">—</div>
      <div class="stat-unit">minutes average</div>
    </div>
    <div class="stat-card orange">
      <div class="stat-label">Longest Streak</div>
      <div class="stat-value orange" id="stat-streak">—</div>
      <div class="stat-unit" id="stat-streak-unit">sessions in a row</div>
    </div>
    <div class="stat-card green">
      <div class="stat-label">Active Weeks</div>
      <div class="stat-value green" id="stat-active-weeks">—</div>
      <div class="stat-unit" id="stat-active-weeks-unit">weeks with a session</div>
    </div>
  </div>
  <div id="sport-split-banner" style="display:flex;gap:12px;margin-bottom:16px;">
    <div style="flex:1;background:linear-gradient(135deg,#06b6d415,#06b6d408);border:1px solid #06b6d440;border-radius:10px;padding:14px 20px;display:flex;align-items:center;gap:14px;">
      <span style="font-size:1.6rem;">🏄</span>
      <div>
        <div style="font-size:0.72rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.06em;font-weight:700;">Kiteboarding</div>
        <div style="font-size:1.4rem;font-weight:800;color:#06b6d4;" id="split-kite-sessions">—</div>
        <div style="font-size:0.75rem;color:#94a3b8;" id="split-kite-detail">— sessions · — km · — h</div>
      </div>
    </div>
    <div style="flex:1;background:linear-gradient(135deg,#8b5cf615,#8b5cf608);border:1px solid #8b5cf640;border-radius:10px;padding:14px 20px;display:flex;align-items:center;gap:14px;">
      <span style="font-size:1.6rem;">🎿</span>
      <div>
        <div style="font-size:0.72rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.06em;font-weight:700;">Snowkiting</div>
        <div style="font-size:1.4rem;font-weight:800;color:#a78bfa;" id="split-snow-sessions">—</div>
        <div style="font-size:0.75rem;color:#94a3b8;" id="split-snow-detail">— sessions · — km · — h</div>
      </div>
    </div>
  </div>

  <!-- ── SORTABLE WIDGETS ── -->
  <div id="widgets-sortable">

    <!-- Calendar -->
    <div class="sortable-item" data-id="calendar">
      <div class="chart-card">
        <div class="widget-drag-handle" title="Drag to reorder">⠿⠿</div>
        <div class="card-title">
          <div class="dot" style="background:#10b981"></div>
          Activity Calendar
          <span style="margin-left:8px;font-size:0.68rem;color:#475569;">Click year to expand · 🟦 kite · 🟪 snow</span>
          <button onclick="calExpandAll()" style="margin-left:auto;background:transparent;border:1px solid #1e293b;color:#64748b;font-size:0.7rem;padding:3px 10px;border-radius:6px;cursor:pointer;transition:all .15s;" onmouseover="this.style.borderColor=\'#334155\'" onmouseout="this.style.borderColor=\'#1e293b\'">Expand all</button>
        </div>
        <div id="cal-heatmap" style="padding-bottom:4px;"></div>
      </div>
    </div>

    <!-- Map + Monthly -->
    <div class="sortable-item" data-id="map-monthly">
      <div class="widget-row-handle"><span class="row-label">GPS Map &amp; Monthly Breakdown</span><span class="row-drag" title="Drag to reorder">⠿⠿</span></div>
      <div class="chart-grid" style="grid-template-columns: 2fr 1fr;margin-bottom:0;">
        <div class="chart-card">
          <div class="card-title">
            <div class="dot" style="background:var(--accent)"></div>
            GPS Tracks
            <span style="font-size:0.72rem;color:var(--text3);font-weight:400;margin-left:auto;">Click track to select · Speed: </span>
            <div class="legend-gradient"></div>
            <span style="font-size:0.72rem;color:var(--text3);">slow→fast</span>
          </div>
          <div id="map"></div>
        </div>
        <div class="chart-card">
          <div class="card-title"><div class="dot" style="background:var(--green)"></div>Sessions by Month <span style="font-size:0.65rem;color:#334155;font-weight:400;margin-left:4px;">per year</span></div>
          <div class="chart-container" style="height:390px;"><canvas id="monthlyChart"></canvas></div>
        </div>
      </div>
    </div>

    <!-- Speed + Distance timelines -->
    <div class="sortable-item" data-id="speed-distance">
      <div class="widget-row-handle"><span class="row-label">Speed &amp; Distance Timeline</span><span class="row-drag" title="Drag to reorder">⠿⠿</span></div>
      <div class="chart-grid" style="margin-bottom:0;">
        <div class="chart-card">
          <div class="card-title">
            <div class="dot" style="background:var(--red)"></div>Speed Over Time
            <span style="font-size:0.65rem;color:#f59e0b;margin-left:8px;">─── EWMA trend</span>
            <span style="margin-left:auto;font-size:0.68rem;color:#334155;font-style:italic;">Click point to open →</span>
          </div>
          <div class="chart-container" style="height:220px;"><canvas id="speedChart"></canvas></div>
        </div>
        <div class="chart-card">
          <div class="card-title">
            <div class="dot" style="background:var(--orange)"></div>Distance &amp; Duration Over Time
            <span style="margin-left:auto;font-size:0.68rem;color:#334155;font-style:italic;">Click bar to open →</span>
          </div>
          <div class="chart-container" style="height:220px;"><canvas id="distanceChart"></canvas></div>
        </div>
      </div>
    </div>

    <!-- Weekly volume -->
    <div class="sortable-item" data-id="weekly-vol">
      <div class="chart-card">
        <div class="widget-drag-handle" title="Drag to reorder">⠿⠿</div>
        <div class="card-title">
          <div class="dot" style="background:#f59e0b"></div>
          Weekly Training Volume
          <span style="font-size:0.72rem;color:var(--text3);font-weight:400;margin-left:8px;">km per week</span>
          <span style="margin-left:auto;font-size:0.68rem;color:#06b6d4;font-weight:600;">─── 4-week rolling avg</span>
        </div>
        <div class="chart-container" style="height:160px;"><canvas id="weeklyVolChart"></canvas></div>
      </div>
    </div>

    <!-- Personal Records -->
    <div class="sortable-item" data-id="personal-records">
      <div class="chart-card">
        <div class="widget-drag-handle" title="Drag to reorder">⠿⠿</div>
        <div class="card-title">
          <div class="dot" style="background:#f59e0b"></div>
          Personal Records
          <span style="font-size:0.7rem;color:#334155;font-weight:400;margin-left:8px;">Click a record to open that session</span>
        </div>
        <div class="pr-grid" id="personal-records"></div>
      </div>
    </div>

    <!-- Stats charts 2×3 -->
    <div class="sortable-item" data-id="stat-charts">
      <div class="widget-row-handle"><span class="row-label">Stats Charts</span><span class="row-drag" title="Drag to reorder">⠿⠿</span></div>
      <div class="chart-grid" style="margin-bottom:0;">
        <div class="chart-card">
          <div class="card-title"><div class="dot" style="background:var(--purple)"></div>Sessions per Year</div>
          <div class="chart-container" style="height:200px;"><canvas id="yearChart"></canvas></div>
        </div>
        <div class="chart-card">
          <div class="card-title"><div class="dot" style="background:var(--green)"></div>Sessions by Day of Week</div>
          <div class="chart-container" style="height:200px;"><canvas id="dowChart"></canvas></div>
        </div>
        <div class="chart-card">
          <div class="card-title">
            <div class="dot" style="background:var(--red)"></div>Speed Zones
            <span style="font-size:0.68rem;color:var(--text3);font-weight:400;margin-left:6px;">max speed per session</span>
          </div>
          <div class="chart-container" style="height:200px;"><canvas id="zonesChart"></canvas></div>
        </div>
        <div class="chart-card">
          <div class="card-title"><div class="dot" style="background:var(--accent)"></div>Max Speed Distribution</div>
          <div class="chart-container" style="height:200px;"><canvas id="speedHistChart"></canvas></div>
        </div>
        <div class="chart-card" style="grid-column: span 2;">
          <div class="card-title"><div class="dot" style="background:#06b6d4"></div>Sessions by Location</div>
          <div class="chart-container" style="height:200px;"><canvas id="locationChart"></canvas></div>
        </div>
      </div>
    </div>

    <!-- Sessions Table -->
    <div class="sortable-item" data-id="table">
      <div class="chart-card">
        <div class="widget-drag-handle" title="Drag to reorder">⠿⠿</div>
        <div class="card-title" style="margin-bottom:12px;">
          <div class="dot" style="background:var(--text3)"></div>
          All Sessions
          <span id="table-count" style="font-size:0.75rem;color:var(--text3);font-weight:400;margin-left:8px;"></span>
          <span style="margin-left:auto;font-size:0.75rem;color:var(--text3);font-weight:400;">Click a row to view details</span>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th data-sort="date" class="sorted"># <span class="sort-arrow">↓</span></th>
                <th data-sort="activity_name">Activity <span class="sort-arrow"></span></th>
                <th data-sort="sport_type">Sport <span class="sort-arrow"></span></th>
                <th data-sort="location">Location <span class="sort-arrow"></span></th>
                <th data-sort="duration_min">Duration <span class="sort-arrow"></span></th>
                <th data-sort="distance_km">Distance <span class="sort-arrow"></span></th>
                <th data-sort="avg_speed_kmh">Avg Speed <span class="sort-arrow"></span></th>
                <th data-sort="max_speed_kmh">Max Speed <span class="sort-arrow"></span></th>
              </tr>
            </thead>
            <tbody id="sessions-table"></tbody>
          </table>
        </div>
      </div>
    </div>

  </div><!-- end #widgets-sortable -->
</div>

<!-- ============ DETAIL PANEL ============ -->
<div class="detail-panel-overlay" id="dp-overlay" onclick="closeDetailPanel()"></div>
<div class="detail-panel" id="detail-panel">
  <div class="dp-header">
    <div class="dp-header-banner" id="dp-banner"></div>
    <div class="dp-header-content">
      <div class="dp-header-top">
        <div style="flex:1;min-width:0;">
          <div class="dp-location" id="dp-location"></div>
          <div class="dp-title" id="dp-title"></div>
          <div class="dp-tags" id="dp-tags"></div>
        </div>
        <button class="dp-close" onclick="closeDetailPanel()">✕</button>
      </div>
    </div>
    <!-- Primary 4-stat bar -->
    <div class="dp-primary-stats" id="dp-primary-stats"></div>
  </div>

  <div class="dp-body">
    <!-- Secondary stats -->
    <div class="dp-secondary-stats" id="dp-secondary-stats"></div>

    <!-- GPS Track Map -->
    <div class="dp-section">Track Map</div>
    <div class="dp-map-wrap" id="dp-map"></div>

    <!-- Speed Over Time -->
    <div class="dp-section">Speed Over Time</div>
    <div class="dp-chart-box">
      <div class="dp-chart-header">
        <div class="dp-chart-label">km/h</div>
        <div class="dp-chart-hint">Hover to explore · position shown on map</div>
      </div>
      <div class="dp-chart-wrap" id="dp-speed-wrap"><canvas id="dp-speed-chart"></canvas></div>
    </div>

    <!-- Elevation Profile -->
    <div id="dp-alt-section">
      <div class="dp-section">Elevation Profile</div>
      <div class="dp-chart-box">
        <div class="dp-chart-header">
          <div class="dp-chart-label">metres</div>
          <div class="dp-chart-hint">Hover to explore · position shown on map</div>
        </div>
        <div class="dp-chart-wrap"><canvas id="dp-alt-chart"></canvas></div>
      </div>
    </div>

    <!-- Heart Rate -->
    <div id="dp-hr-section">
      <div class="dp-section">Heart Rate</div>
      <div class="dp-chart-box">
        <div class="dp-chart-header">
          <div class="dp-chart-label">bpm</div>
          <div class="dp-chart-hint">Hover to explore · position shown on map</div>
        </div>
        <div class="dp-chart-wrap"><canvas id="dp-hr-chart"></canvas></div>
      </div>
    </div>

    <!-- Session vs Average Comparison -->
    <div class="dp-section">vs. Your Average</div>
    <div class="dp-comparison" id="dp-comparison"></div>

    <!-- Radar Performance Profile -->
    <div class="dp-section" id="dp-radar-section" style="display:none;">Performance Profile</div>
    <div id="dp-radar-box" style="display:none;">
      <div class="dp-chart-box">
        <div class="dp-chart-header">
          <div class="dp-chart-label">This session vs sport average</div>
          <div class="dp-chart-hint">Normalised 0–100% of best</div>
        </div>
        <div class="dp-radar-wrap"><canvas id="dp-radar-chart"></canvas></div>
      </div>
    </div>
  </div>
</div>

<script>
// ============================================================
// DATA
// ============================================================
const ALL_SESSIONS = ''' + sessions_json + ''';
const ALL_TRACKS = ''' + tracks_json + ''';
const ALL_TIMESERIES = ''' + timeseries_json + ''';

// ============================================================
// STATE
// ============================================================
let filteredSessions = [...ALL_SESSIONS];
let activeSport = 'all';
let activeYear = 'all';
let activeLocations = new Set(['all']);
let sortKey = 'date';
let sortDir = 1;
let selectedSessionIdx = null;
let map, trackLayers = {}, selectedLayer = null;
let charts = {};

// ============================================================
// INIT
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  buildFilters();
  initMap();
  renderAll();
  updateResetBtn();

  // ── Draggable sections via SortableJS ────────────────────────
  if (typeof Sortable !== 'undefined') {
    Sortable.create(document.getElementById('widgets-sortable'), {
      handle: '.widget-drag-handle, .row-drag',
      animation: 180,
      ghostClass: 'sortable-ghost',
      chosenClass: 'sortable-chosen',
      delay: 80,
      delayOnTouchOnly: true,
      onEnd: () => {
        // After DOM reorder, Chart.js canvases lose context — reinit all
        setTimeout(() => {
          map.invalidateSize();
          updateCharts();
          if (dpMiniMap) dpMiniMap.invalidateSize();
        }, 120);
      }
    });
  }
});

// ============================================================
// FILTERS
// ============================================================
function buildFilters() {
  // Sport type filter buttons
  document.querySelectorAll('[data-sport]').forEach(btn => {
    btn.addEventListener('click', () => {
      activeSport = btn.dataset.sport;
      document.querySelectorAll('[data-sport]').forEach(b => b.classList.toggle('active', b.dataset.sport === activeSport));
      // Update hours unit label
      const unit = document.getElementById('stat-hours-unit');
      if (activeSport === 'kiteboarding') unit.textContent = 'hours on the water';
      else if (activeSport === 'snowkiting') unit.textContent = 'hours on snow';
      else unit.textContent = 'hours total';
      applyFilters();
    });
  });

  const years = [...new Set(ALL_SESSIONS.map(s => s.year))].sort();
  const yearDiv = document.getElementById('year-filters');
  years.forEach(yr => {
    const btn = document.createElement('button');
    btn.className = 'filter-btn';
    btn.textContent = yr;
    btn.dataset.year = yr;
    btn.addEventListener('click', () => setYearFilter(yr, btn));
    yearDiv.appendChild(btn);
  });
  
  const locs = [...new Set(ALL_SESSIONS.map(s => s.location || 'Unknown'))].sort();
  const locDiv = document.getElementById('loc-filters');
  const allBtn = document.createElement('button');
  allBtn.className = 'filter-btn active';
  allBtn.textContent = 'All';
  allBtn.dataset.loc = 'all';
  allBtn.addEventListener('click', () => setLocFilter('all'));
  locDiv.appendChild(allBtn);
  locs.forEach(loc => {
    const btn = document.createElement('button');
    btn.className = 'filter-btn';
    btn.textContent = loc;
    btn.dataset.loc = loc;
    btn.addEventListener('click', () => setLocFilter(loc, btn));
    locDiv.appendChild(btn);
  });
}

function setYearFilter(year) {
  const y = String(year);
  activeYear = (activeYear === y) ? 'all' : y;
  document.querySelectorAll('[data-year]').forEach(b => {
    b.classList.toggle('active', b.dataset.year === activeYear);
  });
  applyFilters();
}

function setLocFilter(loc) {
  if (loc === 'all') {
    activeLocations = new Set(['all']);
  } else {
    activeLocations.delete('all');
    if (activeLocations.has(loc)) activeLocations.delete(loc);
    else activeLocations.add(loc);
    if (activeLocations.size === 0) activeLocations.add('all');
  }
  document.querySelectorAll('[data-loc]').forEach(b => {
    const l = b.dataset.loc;
    b.classList.toggle('active', l === 'all' ? activeLocations.has('all') : activeLocations.has(l));
  });
  applyFilters();
}

function applyFilters() {
  filteredSessions = ALL_SESSIONS.filter(s => {
    if (activeSport !== 'all' && s.sport_type !== activeSport) return false;
    if (activeYear !== 'all' && String(s.year) !== activeYear) return false;
    if (!activeLocations.has('all') && !activeLocations.has(s.location || 'Unknown')) return false;
    return true;
  });
  updateResetBtn();
  renderAll();
}

function updateResetBtn() {
  const isFiltered = activeSport !== 'all' || activeYear !== 'all' || !activeLocations.has('all');
  const btn = document.getElementById('reset-filters-btn');
  if (btn) btn.style.display = isFiltered ? 'flex' : 'none';
}

function resetAllFilters() {
  activeSport = 'all';
  activeYear = 'all';
  activeLocations = new Set(['all']);
  document.querySelectorAll('[data-sport]').forEach(b => b.classList.toggle('active', b.dataset.sport === 'all'));
  document.querySelectorAll('[data-year]').forEach(b => b.classList.toggle('active', b.dataset.year === 'all'));
  document.querySelectorAll('[data-loc]').forEach(b => b.classList.toggle('active', b.dataset.loc === 'all'));
  const unit = document.getElementById('stat-hours-unit');
  if (unit) unit.textContent = 'hours total';
  applyFilters();
}

// ============================================================
// RENDER ALL
// ============================================================
function renderAll() {
  updateStats();
  updateTable();
  updateCharts();
  updateMapTracks();
}

// ============================================================
// STATS
// ============================================================
// ── Streak & consistency helpers ────────────────────────────────────────────
function getISOWeekKey(dateStr) {
  const [y, m, d] = dateStr.split('-').map(Number);
  const dt = new Date(y, m - 1, d);
  // ISO week: find Thursday of same week, then compute week number
  const dayOfWeek = dt.getDay() === 0 ? 7 : dt.getDay(); // Mon=1..Sun=7
  const thursday = new Date(dt);
  thursday.setDate(dt.getDate() + (4 - dayOfWeek));
  const yearStart = new Date(thursday.getFullYear(), 0, 1);
  const weekNum = Math.ceil(((thursday - yearStart) / 86400000 + 1) / 7);
  return `${thursday.getFullYear()}-W${String(weekNum).padStart(2, '0')}`;
}

function calcConsistency(sessions) {
  if (sessions.length === 0) return { maxStreak: 0, activeWeeks: 0 };
  const sorted = [...sessions].sort((a, b) => a.date < b.date ? -1 : 1);
  // Longest streak: consecutive sessions within 14 days of each other
  let maxStreak = 1, cur = 1;
  for (let i = 1; i < sorted.length; i++) {
    const [ay, am, ad] = sorted[i-1].date.split('-').map(Number);
    const [by, bm, bd] = sorted[i].date.split('-').map(Number);
    const diff = (new Date(by, bm-1, bd) - new Date(ay, am-1, ad)) / 86400000;
    if (diff <= 14) { cur++; maxStreak = Math.max(maxStreak, cur); }
    else cur = 1;
  }
  // Active weeks (unique ISO weeks)
  const weeks = new Set(sorted.filter(s => s.date).map(s => getISOWeekKey(s.date)));
  return { maxStreak, activeWeeks: weeks.size };
}

function updateStats() {
  const n = filteredSessions.length;
  const hours = filteredSessions.reduce((s, x) => s + (x.duration_min || 0), 0) / 60;
  const dist = filteredSessions.reduce((s, x) => s + (x.distance_km || 0), 0);
  const _spdVals = filteredSessions.map(x => x.max_speed_kmh || 0);
  const maxSpd = _spdVals.length ? Math.max(..._spdVals) : 0;
  const avgMovSpd = filteredSessions.filter(x => x.avg_speed_kmh).reduce((s, x) => s + x.avg_speed_kmh, 0) / filteredSessions.filter(x => x.avg_speed_kmh).length;
  const avgDur = filteredSessions.filter(x => x.duration_min).reduce((s, x) => s + x.duration_min, 0) / filteredSessions.filter(x => x.duration_min).length;

  document.getElementById('stat-sessions').textContent = n;
  document.getElementById('stat-hours').textContent = hours.toFixed(0);
  document.getElementById('stat-distance').textContent = dist.toFixed(0);
  document.getElementById('stat-maxspeed').textContent = maxSpd.toFixed(1);
  document.getElementById('stat-avgspeed').textContent = (avgMovSpd || 0).toFixed(1);
  document.getElementById('stat-avgsession').textContent = (avgDur || 0).toFixed(0);

  // Streak & consistency
  const { maxStreak, activeWeeks } = calcConsistency(filteredSessions);
  document.getElementById('stat-streak').textContent = maxStreak;
  document.getElementById('stat-active-weeks').textContent = activeWeeks;
  
  const sorted = [...filteredSessions].sort((a,b) => (b.start_timestamp||0) - (a.start_timestamp||0));
  document.getElementById('last-session-date').textContent = sorted[0]?.date || '—';

  const dateRange = filteredSessions.length ? `${sorted[sorted.length-1].date} → ${sorted[0].date} · ${n} sessions` : 'No sessions';
  document.getElementById('header-subtitle').textContent = dateRange;

  // Sport split banner — always uses ALL_SESSIONS so it doesn't disappear when filtering
  const baseSessions = activeSport === 'all' ? filteredSessions : ALL_SESSIONS.filter(s => {
    if (activeYear !== 'all' && String(s.year) !== activeYear) return false;
    if (!activeLocations.has('all') && !activeLocations.has(s.location || 'Unknown')) return false;
    return true;
  });
  const kiteSess = baseSessions.filter(s => s.sport_type === 'kiteboarding');
  const snowSess = baseSessions.filter(s => s.sport_type === 'snowkiting');
  const kiteDist = kiteSess.reduce((s,x) => s+(x.distance_km||0),0);
  const snowDist = snowSess.reduce((s,x) => s+(x.distance_km||0),0);
  const kiteH = kiteSess.reduce((s,x) => s+(x.duration_min||0),0)/60;
  const snowH = snowSess.reduce((s,x) => s+(x.duration_min||0),0)/60;
  document.getElementById('split-kite-sessions').textContent = kiteSess.length + ' sessions';
  document.getElementById('split-snow-sessions').textContent = snowSess.length + ' sessions';
  document.getElementById('split-kite-detail').textContent = `${kiteDist.toFixed(0)} km · ${kiteH.toFixed(1)} h`;
  document.getElementById('split-snow-detail').textContent = `${snowDist.toFixed(0)} km · ${snowH.toFixed(1)} h`;
}

// ============================================================
// MAP
// ============================================================
function initMap() {
  map = L.map('map', { zoomControl: true, attributionControl: false });
  
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
    attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ', maxZoom: 16
  }).addTo(map);
  
  map.setView([59.5, 10.5], 7);
}

function speedToColor(spd, maxSpd, sportType) {
  if (!spd || !maxSpd) return sportType === 'snowkiting' ? '#8b5cf6' : '#06b6d4';
  const ratio = Math.min(1, spd / Math.min(maxSpd * 0.9, 50));
  if (sportType === 'snowkiting') {
    // Purple → blue → white for snowkiting
    if (ratio < 0.5) return `hsl(${270 - ratio*40}, 70%, ${50 + ratio*15}%)`;
    return `hsl(${230 - (ratio-0.5)*40}, 65%, ${65 + (ratio-0.5)*20}%)`;
  }
  // Cyan → orange → red for kiteboarding (original)
  if (ratio < 0.33) return `hsl(${185 + ratio * 60}, 80%, 55%)`;
  if (ratio < 0.66) return `hsl(${40 + (ratio-0.33)*60}, 90%, 55%)`;
  return `hsl(${20 - (ratio-0.66)*30}, 85%, 55%)`;
}

function updateMapTracks() {
  // Remove existing layers
  Object.values(trackLayers).forEach(layers => layers.forEach(l => map.removeLayer(l)));
  trackLayers = {};
  
  const visibleFilenames = new Set(filteredSessions.map(s => s.filename));
  
  filteredSessions.forEach(session => {
    const track = ALL_TRACKS[session.filename];
    if (!track || track.length < 2) return;
    
    const maxTrackSpd = Math.max(...track.map(p => p.spd || 0));
    
    // Build colored polyline segments
    const layers = [];
    let segPoints = [track[0]];
    
    for (let i = 1; i < track.length; i++) {
      segPoints.push(track[i]);
      if (segPoints.length >= 5 || i === track.length - 1) {
        const avgSpd = segPoints.reduce((s, p) => s + (p.spd || 0), 0) / segPoints.length;
        const color = speedToColor(avgSpd, maxTrackSpd, session.sport_type);
        const line = L.polyline(
          segPoints.map(p => [p.lat, p.lon]),
          { color, weight: 2, opacity: 0.6, smoothFactor: 1.5 }
        );
        line.on('click', () => selectSession(session));
        layers.push(line);
        segPoints = [track[i]];
      }
    }
    
    layers.forEach(l => l.addTo(map));
    trackLayers[session.filename] = layers;
  });
  
  // Fit bounds to visible tracks
  const allPts = [];
  filteredSessions.forEach(s => {
    const t = ALL_TRACKS[s.filename];
    if (t) allPts.push(...t.map(p => [p.lat, p.lon]));
  });
  if (allPts.length > 0) {
    try { map.fitBounds(L.latLngBounds(allPts), { padding: [20, 20], maxZoom: 12 }); } catch(e) {}
  }
}

let dpMiniMap = null;
let dpSpeedChart = null;
let dpAltChart = null;
let dpHrChart = null;
let dpRadarChart = null;
let dpHoverMarker = null;  // pulsing marker on mini-map while hovering a chart
let dpCurrentTrack = null; // filtered valid track pts for current session

// ─── Crosshair + map-sync plugin (registered globally) ───────────────────────
const dpCrosshairPlugin = {
  id: 'dpCrosshair',
  afterDraw(chart) {
    if (!chart.chartArea) return;
    const active = chart.tooltip?._active;
    if (!active || active.length === 0) return;
    const ctx2 = chart.ctx;
    const x = active[0].element.x;
    const { top, bottom } = chart.chartArea;
    ctx2.save();
    ctx2.beginPath();
    ctx2.moveTo(x, top);
    ctx2.lineTo(x, bottom);
    ctx2.strokeStyle = 'rgba(255,255,255,0.22)';
    ctx2.lineWidth = 1;
    ctx2.setLineDash([4, 3]);
    ctx2.stroke();
    ctx2.restore();
    // Sync map marker
    const idx = active[0].index;
    const total = chart.data.labels.length;
    updateDpMapMarker(idx, total);
  }
};
Chart.register(dpCrosshairPlugin);

function updateDpMapMarker(dataIdx, totalPts) {
  if (!dpMiniMap || !dpCurrentTrack || dpCurrentTrack.length === 0) return;
  const tIdx = Math.round(Math.min(dataIdx, totalPts - 1) / (totalPts - 1) * (dpCurrentTrack.length - 1));
  const pt = dpCurrentTrack[Math.max(0, Math.min(tIdx, dpCurrentTrack.length - 1))];
  if (!pt) return;
  if (!dpHoverMarker) {
    dpHoverMarker = L.circleMarker([pt.lat, pt.lon], {
      radius: 7, color: '#fff', fillColor: '#facc15', fillOpacity: 1, weight: 2.5,
      className: 'dp-hover-marker'
    }).addTo(dpMiniMap);
  } else {
    dpHoverMarker.setLatLng([pt.lat, pt.lon]);
  }
}

function selectSession(session) {
  // Highlight track on main map
  Object.entries(trackLayers).forEach(([fn, layers]) => {
    layers.forEach(l => {
      if (fn === session.filename) { l.setStyle({ weight: 4, opacity: 1 }); l.bringToFront(); }
      else { l.setStyle({ weight: 1.5, opacity: 0.2 }); }
    });
  });
  const track = ALL_TRACKS[session.filename];
  if (track && track.length > 0) {
    map.fitBounds(L.latLngBounds(track.map(p => [p.lat, p.lon])), { padding: [30, 30] });
  }
  selectedSessionIdx = session.filename;
  document.querySelectorAll('#sessions-table tr').forEach(row => {
    row.classList.toggle('selected', row.dataset.filename === session.filename);
  });
  const selRow = document.querySelector(`tr[data-filename="${session.filename}"]`);
  if (selRow) selRow.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  openDetailPanel(session);
}

function makeDpChart(canvasId, labels, vals, borderColor, unit, tooltipFmt) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return null;
  const c = ctx.getContext('2d');
  const grad = c.createLinearGradient(0, 0, 0, 120);
  grad.addColorStop(0, borderColor + '45');
  grad.addColorStop(1, borderColor + '03');
  return new Chart(c, {
    type: 'line',
    data: { labels, datasets: [{ data: vals, borderColor, backgroundColor: grad,
      borderWidth: 2, pointRadius: 0, pointHoverRadius: 5,
      pointHoverBackgroundColor: borderColor, pointHoverBorderColor: '#fff',
      pointHoverBorderWidth: 2,
      fill: true, tension: 0.35 }] },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(10,18,35,0.97)', bodyColor: '#e2e8f0',
          titleColor: '#64748b', borderColor: '#334155', borderWidth: 1,
          padding: 10, cornerRadius: 8, displayColors: false,
          callbacks: {
            label: ctx => '  ' + tooltipFmt(ctx.parsed.y),
            title: ctx => '⏱ ' + ctx[0].label + ' min'
          }
        }
      },
      scales: {
        x: { display: true, ticks: { color: '#475569', maxTicksLimit: 6, font:{size:9} }, grid: { color: 'rgba(30,41,59,0.3)' } },
        y: { display: true, ticks: { color: '#475569', font:{size:9} }, grid: { color: 'rgba(30,41,59,0.3)' },
             title: { display: true, text: unit, color: '#475569', font:{size:9} } }
      }
    }
  });
}

function openDetailPanel(session) {
  const sportColor = session.sport_type === 'kiteboarding' ? '#06b6d4' : '#a78bfa';
  const sportLabel = session.sport_type === 'kiteboarding' ? '🏄 Kiteboarding' : '🎿 Snowkiting';

  // ── Banner strip ─────────────────────────────────────────────
  const banner = document.getElementById('dp-banner');
  if (banner) banner.style.background = `linear-gradient(90deg, ${sportColor}, ${sportColor}55)`;

  // ── Header text ──────────────────────────────────────────────
  const locEl = document.getElementById('dp-location');
  if (locEl) locEl.textContent = '📍 ' + (session.location || 'Unknown location');

  const titleEl = document.getElementById('dp-title');
  if (titleEl) {
    // Activity name as primary title, date as subtitle
    if (session.activity_name) {
      titleEl.innerHTML = session.activity_name +
        `<div style="font-size:0.82rem;font-weight:500;color:#64748b;margin-top:3px;">${session.date}</div>`;
    } else {
      const d = new Date(session.date);
      const dayNames = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
      const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      titleEl.textContent = `${dayNames[d.getDay()]}, ${d.getDate()} ${monthNames[d.getMonth()]} ${d.getFullYear()}`;
    }
  }

  const tagsEl = document.getElementById('dp-tags');
  if (tagsEl) {
    const durStr = session.duration_min ? (() => {
      const h = Math.floor(session.duration_min / 60);
      const m = Math.round(session.duration_min % 60);
      return h > 0 ? `${h}h ${m}m` : `${m} min`;
    })() : null;
    tagsEl.innerHTML = `
      <span class="dp-tag" style="background:${sportColor}22;color:${sportColor};">${sportLabel}</span>
      ${durStr ? `<span class="dp-tag">${durStr}</span>` : ''}
      ${session.distance_km ? `<span class="dp-tag">${session.distance_km.toFixed(1)} km</span>` : ''}
      ${session.year ? `<span class="dp-tag" style="background:transparent;color:#475569;padding-left:4px;">${session.year}</span>` : ''}
    `;
  }

  // ── Primary stats (4-across bar) ─────────────────────────────
  const primaryEl = document.getElementById('dp-primary-stats');
  if (primaryEl) {
    const maxSpeedStr = session.max_speed_kmh ? session.max_speed_kmh.toFixed(1) : '—';
    const avgSpeedStr = session.avg_speed_kmh ? session.avg_speed_kmh.toFixed(1) : '—';
    const distStr = session.distance_km ? session.distance_km.toFixed(1) : '—';
    const durStr = session.duration_min ? (() => {
      const h = Math.floor(session.duration_min / 60);
      const m = Math.round(session.duration_min % 60);
      return h > 0 ? `${h}<small>h</small>${m}<small>m</small>` : `${m}<small>m</small>`;
    })() : '—';
    primaryEl.innerHTML = `
      <div class="dp-primary-stat">
        <div class="dp-primary-stat-val" style="color:#ef4444">${maxSpeedStr}</div>
        <div class="dp-primary-stat-label">Max Speed<br><span style="font-size:0.7rem;color:#64748b;">km/h</span></div>
      </div>
      <div class="dp-primary-stat">
        <div class="dp-primary-stat-val" style="color:#f59e0b">${avgSpeedStr}</div>
        <div class="dp-primary-stat-label">Avg Speed<br><span style="font-size:0.7rem;color:#64748b;">km/h</span></div>
      </div>
      <div class="dp-primary-stat">
        <div class="dp-primary-stat-val" style="color:#10b981">${distStr}</div>
        <div class="dp-primary-stat-label">Distance<br><span style="font-size:0.7rem;color:#64748b;">km</span></div>
      </div>
      <div class="dp-primary-stat" style="border-right:none">
        <div class="dp-primary-stat-val" style="color:${sportColor}">${durStr}</div>
        <div class="dp-primary-stat-label">Duration</div>
      </div>
    `;
  }

  // ── Secondary stats (grid cards) ────────────────────────────
  const secEl = document.getElementById('dp-secondary-stats');
  if (secEl) {
    const cards = [];
    if (session.avg_hr || session.max_hr) {
      cards.push(`<div class="dp-sec-stat">
        <div class="dp-sec-label">❤️ Heart Rate</div>
        <div class="dp-sec-val">${session.avg_hr ? session.avg_hr + '<span style="font-size:0.7rem;color:#64748b;"> avg</span>' : '—'}</div>
        ${session.max_hr ? `<div style="font-size:0.75rem;color:#f43f5e;margin-top:2px;">${session.max_hr} bpm max</div>` : ''}
      </div>`);
    }
    if (session.calories) {
      cards.push(`<div class="dp-sec-stat">
        <div class="dp-sec-label">🔥 Calories</div>
        <div class="dp-sec-val">${session.calories}<span style="font-size:0.7rem;color:#64748b;"> kcal</span></div>
      </div>`);
    }
    if (session.avg_alt != null || session.max_alt != null) {
      const altStr = session.avg_alt != null ? session.avg_alt + 'm' : (session.max_alt != null ? session.max_alt + 'm' : '—');
      const rangeStr = (session.min_alt != null && session.max_alt != null) ? `${session.min_alt}–${session.max_alt} m` : '';
      cards.push(`<div class="dp-sec-stat">
        <div class="dp-sec-label">⛰️ Altitude</div>
        <div class="dp-sec-val">${altStr}</div>
        ${rangeStr ? `<div style="font-size:0.75rem;color:#64748b;margin-top:2px;">${rangeStr} range</div>` : ''}
      </div>`);
    }
    if (session.total_ascent || session.total_descent) {
      cards.push(`<div class="dp-sec-stat">
        <div class="dp-sec-label">📈 Climb</div>
        <div class="dp-sec-val">${session.total_ascent ? '↑' + Math.round(session.total_ascent) + 'm' : ''}${session.total_descent ? ' ↓' + Math.round(session.total_descent) + 'm' : ''}</div>
      </div>`);
    }
    if (session.avg_temp != null) {
      cards.push(`<div class="dp-sec-stat">
        <div class="dp-sec-label">🌡️ Temperature</div>
        <div class="dp-sec-val">${session.avg_temp}°C</div>
        ${session.min_temp != null && session.max_temp != null ? `<div style="font-size:0.75rem;color:#64748b;margin-top:2px;">${session.min_temp}–${session.max_temp}°C</div>` : ''}
      </div>`);
    }
    if (cards.length === 0) {
      secEl.innerHTML = '<div style="color:#475569;font-size:0.8rem;grid-column:1/-1;padding:6px 0;">No additional metrics recorded</div>';
    } else {
      secEl.innerHTML = cards.join('');
    }
  }

  // ── Mini map ─────────────────────────────────────────────────
  dpCurrentTrack = null;
  if (dpHoverMarker) { dpHoverMarker.remove(); dpHoverMarker = null; }
  setTimeout(() => {
    if (dpMiniMap) { dpMiniMap.remove(); dpMiniMap = null; }
    const mapEl = document.getElementById('dp-map');
    if (mapEl) {
      dpMiniMap = L.map('dp-map', { zoomControl: true, attributionControl: false, scrollWheelZoom: false });
      L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri', maxZoom: 16
      }).addTo(dpMiniMap);
      const rawTrack = ALL_TRACKS[session.filename];
      if (rawTrack && rawTrack.length > 1) {
        const vt = rawTrack.filter(p => p.lat !== 180.0 && p.lon !== 180.0 && Math.abs(p.lat) <= 85 && Math.abs(p.lon) <= 179);
        if (vt.length > 1) {
          dpCurrentTrack = vt; // store for hover sync
          const maxSpd = Math.max(...vt.map(p => p.spd || 0));
          let seg = [vt[0]];
          for (let i = 1; i < vt.length; i++) {
            seg.push(vt[i]);
            if (seg.length >= 5 || i === vt.length - 1) {
              const avgS = seg.reduce((a,p) => a+(p.spd||0),0)/seg.length;
              L.polyline(seg.map(p => [p.lat,p.lon]), {
                color: speedToColor(avgS, maxSpd, session.sport_type), weight: 3, opacity: 0.95
              }).addTo(dpMiniMap);
              seg = [vt[i]];
            }
          }
          dpMiniMap.fitBounds(L.latLngBounds(vt.map(p => [p.lat,p.lon])), {padding:[18,18]});
          L.circleMarker([vt[0].lat, vt[0].lon], {radius:6, color:'#10b981', fillColor:'#10b981', fillOpacity:1, weight:2}).bindTooltip('Start', {permanent:false, direction:'top'}).addTo(dpMiniMap);
          const last = vt[vt.length-1];
          L.circleMarker([last.lat, last.lon], {radius:6, color:'#ef4444', fillColor:'#ef4444', fillOpacity:1, weight:2}).bindTooltip('End', {permanent:false, direction:'top'}).addTo(dpMiniMap);
        }
      } else if (session.centroid_lat) {
        dpMiniMap.setView([session.centroid_lat, session.centroid_lon], 11);
      }
      dpMiniMap.invalidateSize();
    }
  }, 60);

  // ── Charts ────────────────────────────────────────────────────
  if (dpSpeedChart) { dpSpeedChart.destroy(); dpSpeedChart = null; }
  if (dpAltChart) { dpAltChart.destroy(); dpAltChart = null; }
  if (dpHrChart) { dpHrChart.destroy(); dpHrChart = null; }

  const tsData = ALL_TIMESERIES[session.filename];
  const speedColor = session.sport_type === 'kiteboarding' ? '#06b6d4' : '#8b5cf6';

  // Speed chart
  const speedWrap = document.getElementById('dp-speed-wrap');
  if (speedWrap) {
    if (tsData && tsData.speed && tsData.speed.length > 2) {
      const vSpd = tsData.speed.filter(p => p[1] !== null && p[1] >= 0 && p[1] < 200);
      if (vSpd.length > 2) {
        speedWrap.innerHTML = '<canvas id="dp-speed-chart"></canvas>';
        dpSpeedChart = makeDpChart('dp-speed-chart', vSpd.map(p => p[0].toFixed(1)), vSpd.map(p => p[1]),
          speedColor, 'km/h', v => v.toFixed(1) + ' km/h');
      } else {
        speedWrap.innerHTML = '<div class="dp-no-data">No speed data recorded</div>';
      }
    } else {
      speedWrap.innerHTML = '<div class="dp-no-data">No speed data recorded</div>';
    }
  }

  // Altitude chart
  const altSection = document.getElementById('dp-alt-section');
  if (altSection) {
    if (session.has_alt && tsData && tsData.alt && tsData.alt.length > 2) {
      const vAlt = tsData.alt.filter(p => p[1] !== null && p[1] > -200 && p[1] < 5000);
      if (vAlt.length > 2) {
        altSection.style.display = '';
        const altWrap = altSection.querySelector('.dp-chart-wrap');
        if (altWrap) {
          altWrap.innerHTML = '<canvas id="dp-alt-chart"></canvas>';
          dpAltChart = makeDpChart('dp-alt-chart', vAlt.map(p => p[0].toFixed(1)), vAlt.map(p => p[1]),
            '#34d399', 'm', v => v.toFixed(0) + ' m');
        }
      } else {
        altSection.style.display = 'none';
      }
    } else {
      altSection.style.display = 'none';
    }
  }

  // HR chart
  const hrSection = document.getElementById('dp-hr-section');
  if (hrSection) {
    if (session.has_hr && tsData && tsData.hr && tsData.hr.length > 2) {
      const vHr = tsData.hr.filter(p => p[1] !== null && p[1] > 40 && p[1] < 250);
      if (vHr.length > 2) {
        hrSection.style.display = '';
        const hrWrap = hrSection.querySelector('.dp-chart-wrap');
        if (hrWrap) {
          hrWrap.innerHTML = '<canvas id="dp-hr-chart"></canvas>';
          dpHrChart = makeDpChart('dp-hr-chart', vHr.map(p => p[0].toFixed(1)), vHr.map(p => p[1]),
            '#f43f5e', 'bpm', v => v.toFixed(0) + ' bpm');
        }
      } else {
        hrSection.style.display = 'none';
      }
    } else {
      hrSection.style.display = 'none';
    }
  }

  // ── Comparison vs averages ────────────────────────────────────
  const cmpEl = document.getElementById('dp-comparison');
  if (cmpEl) {
    const sameType = ALL_SESSIONS.filter(s => s.sport_type === session.sport_type);
    const allSess = ALL_SESSIONS;

    function cmpRow(label, val, allVals, fmt, color, isPB) {
      const valid = allVals.filter(Boolean);
      if (!val || valid.length === 0) return '';
      const avg = valid.reduce((a,b) => a+b, 0) / valid.length;
      const best = Math.max(...valid);
      const pct = valid.filter(v => v < val).length / valid.length;
      const barPct = Math.min(100, (val / best) * 100);
      const pbBadge = isPB ? '<span style="background:#f59e0b22;color:#f59e0b;font-size:0.65rem;font-weight:700;padding:1px 6px;border-radius:10px;margin-left:6px;">🏆 PB</span>' :
                     pct > 0.85 ? '<span style="background:#10b98122;color:#10b981;font-size:0.65rem;font-weight:700;padding:1px 6px;border-radius:10px;margin-left:6px;">Top 15%</span>' :
                     pct > 0.7 ? '<span style="background:#3b82f622;color:#60a5fa;font-size:0.65rem;font-weight:700;padding:1px 6px;border-radius:10px;margin-left:6px;">Top 30%</span>' : '';
      return `<div class="dp-cmp-row">
        <div style="min-width:120px;font-size:0.78rem;color:#94a3b8;">${label}</div>
        <div class="dp-cmp-bar-wrap"><div style="height:100%;width:${barPct}%;background:${color};border-radius:3px;"></div></div>
        <div style="flex:1;font-size:0.82rem;font-weight:600;color:#e2e8f0;">${fmt(val)} <span style="font-size:0.72rem;color:#475569;">avg ${fmt(avg)}</span>${pbBadge}</div>
      </div>`;
    }

    const maxSpd = session.max_speed_kmh;
    const bestSpd = Math.max(...sameType.map(s => s.max_speed_kmh || 0));
    const bestDist = Math.max(...sameType.map(s => s.distance_km || 0));
    const bestDur = Math.max(...sameType.map(s => s.duration_min || 0));

    cmpEl.innerHTML = [
      cmpRow('Max Speed', maxSpd, sameType.map(s=>s.max_speed_kmh), v => v.toFixed(1)+' km/h', '#ef4444', maxSpd === bestSpd),
      cmpRow('Avg Speed', session.avg_speed_kmh, sameType.map(s=>s.avg_speed_kmh), v => v.toFixed(1)+' km/h', '#f59e0b', false),
      cmpRow('Distance', session.distance_km, sameType.map(s=>s.distance_km), v => v.toFixed(1)+' km', '#10b981', session.distance_km === bestDist),
      cmpRow('Duration', session.duration_min, sameType.map(s=>s.duration_min), v => {
        const h=Math.floor(v/60),m=Math.round(v%60); return h>0?`${h}h ${m}m`:`${m}m`;
      }, sportColor, session.duration_min === bestDur),
    ].filter(Boolean).join('') || '<div style="color:#475569;font-size:0.8rem;padding:6px 0;">No comparison data available</div>';
  }

  // ── Radar performance profile ─────────────────────────────────
  if (dpRadarChart) { dpRadarChart.destroy(); dpRadarChart = null; }
  const radarSection = document.getElementById('dp-radar-section');
  const radarBox     = document.getElementById('dp-radar-box');
  const radarCanvas  = document.getElementById('dp-radar-chart');
  if (radarSection && radarBox && radarCanvas) {
    const sameType  = ALL_SESSIONS.filter(s => s.sport_type === session.sport_type);
    const metrics   = ['Max Speed', 'Avg Speed', 'Distance', 'Duration', 'HR (avg)'];
    const fields    = ['max_speed_kmh', 'avg_speed_kmh', 'distance_km', 'duration_min', 'avg_hr'];

    function normTo100(val, field) {
      const allVals = sameType.map(s => s[field]).filter(v => v != null && v > 0);
      const mx = allVals.length ? Math.max(...allVals) : 1;
      return mx > 0 ? Math.round((val || 0) / mx * 100) : 0;
    }
    function avgField(field) {
      const vs = sameType.map(s => s[field]).filter(v => v != null && v > 0);
      return vs.length ? vs.reduce((a,b) => a+b, 0) / vs.length : 0;
    }

    const sessVals = fields.map(f => normTo100(session[f], f));
    const avgVals  = fields.map(f => normTo100(avgField(f), f));
    const hasHR    = session.avg_hr && session.avg_hr > 0;

    // Show only if we have meaningful data (at least 3 non-zero values)
    if (sessVals.filter(v => v > 0).length >= 3) {
      radarSection.style.display = '';
      radarBox.style.display = '';
      const displayMetrics = hasHR ? metrics : metrics.slice(0, 4);
      const displaySess    = hasHR ? sessVals : sessVals.slice(0, 4);
      const displayAvg     = hasHR ? avgVals  : avgVals.slice(0, 4);

      dpRadarChart = new Chart(radarCanvas.getContext('2d'), {
        type: 'radar',
        data: {
          labels: displayMetrics,
          datasets: [
            {
              label: 'This session',
              data: displaySess,
              borderColor: sportColor,
              backgroundColor: sportColor + '25',
              borderWidth: 2,
              pointRadius: 4,
              pointHoverRadius: 6,
              pointBackgroundColor: sportColor
            },
            {
              label: 'Sport average',
              data: displayAvg,
              borderColor: '#475569',
              backgroundColor: 'rgba(71,85,105,0.1)',
              borderWidth: 1.5,
              pointRadius: 3,
              borderDash: [4, 3],
              pointBackgroundColor: '#475569'
            }
          ]
        },
        options: {
          responsive: true, maintainAspectRatio: false, animation: false,
          scales: {
            r: {
              min: 0, max: 100,
              angleLines: { color: 'rgba(30,41,59,0.6)' },
              grid: { color: 'rgba(30,41,59,0.6)' },
              pointLabels: { color: '#94a3b8', font: { size: 10 } },
              ticks: { display: false, stepSize: 25 }
            }
          },
          plugins: {
            legend: {
              display: true, position: 'bottom',
              labels: { color: '#64748b', font: { size: 9 }, boxWidth: 10, padding: 8 }
            },
            tooltip: {
              backgroundColor: 'rgba(10,18,35,0.97)', bodyColor: '#94a3b8',
              borderColor: '#334155', borderWidth: 1, padding: 8, cornerRadius: 8,
              callbacks: { label: item => `  ${item.dataset.label}: ${item.parsed.r}%` }
            }
          }
        }
      });
    } else {
      radarSection.style.display = 'none';
      radarBox.style.display = 'none';
    }
  }

  // ── Open panel ───────────────────────────────────────────────
  document.getElementById('detail-panel').classList.add('open');
  document.getElementById('dp-overlay').classList.add('open');
}

function closeDetailPanel() {
  document.getElementById('detail-panel').classList.remove('open');
  document.getElementById('dp-overlay').classList.remove('open');
  Object.values(trackLayers).forEach(layers => layers.forEach(l => l.setStyle({ weight: 2, opacity: 0.6 })));
  selectedSessionIdx = null;
  dpCurrentTrack = null;
  if (dpHoverMarker) { dpHoverMarker.remove(); dpHoverMarker = null; }
  if (dpRadarChart) { dpRadarChart.destroy(); dpRadarChart = null; }
  document.querySelectorAll('#sessions-table tr').forEach(r => r.classList.remove('selected'));
}

function resetMapSelection() {
  Object.values(trackLayers).forEach(layers => layers.forEach(l => l.setStyle({ weight: 2, opacity: 0.6 })));
  selectedSessionIdx = null;
  document.querySelectorAll('#sessions-table tr').forEach(r => r.classList.remove('selected'));
  updateMapTracks();
}

// ============================================================
// TABLE
// ============================================================
function updateTable() {
  const sorted = [...filteredSessions].sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey];
    if (av == null) return 1;
    if (bv == null) return -1;
    return sortDir * (av < bv ? -1 : av > bv ? 1 : 0);
  });
  
  document.getElementById('table-count').textContent = `(${sorted.length})`;
  
  const tbody = document.getElementById('sessions-table');
  tbody.innerHTML = '';
  
  const maxDist = Math.max(...sorted.map(s => s.distance_km || 0));
  const maxSpd = Math.max(...sorted.map(s => s.max_speed_kmh || 0));
  
  sorted.forEach((s, i) => {
    const tr = document.createElement('tr');
    tr.dataset.filename = s.filename;
    if (s.filename === selectedSessionIdx) tr.classList.add('selected');
    
    const rank = sortDir === 1 ? i + 1 : sorted.length - i;
    
    const distBar = s.distance_km ? `<span class="speed-bar" style="width:${(s.distance_km/maxDist*40).toFixed(0)}px"></span>` : '';
    const spdBar = s.max_speed_kmh ? `<span class="speed-bar" style="width:${(s.max_speed_kmh/maxSpd*40).toFixed(0)}px;background:linear-gradient(90deg,var(--red),#f87171)"></span>` : '';
    
    const locColor = {
      'Adur, West Sussex': '#f59e0b',
      'United Kingdom': '#f59e0b',
      'Thyborøn, Denmark': '#06b6d4',
      'Thisted, Denmark': '#0891b2',
      'Denmark': '#22d3ee',
      'Vear, Tønsberg': '#10b981',
      'Rygge, Oslofjord': '#34d399',
      'Hurum, Oslofjord': '#6ee7b7',
      'Eidfjord, Hardangervidda': '#8b5cf6',
      'Hol, Hardangervidda': '#a78bfa',
      'Nore og Uvdal': '#c4b5fd',
      'Hemsedal / Dagali': '#3b82f6',
      'Øystre Slidre, Valdres': '#60a5fa',
      'Vang, Valdres': '#93c5fd',
      'Lom, Jotunheimen': '#f97316',
      'Røros': '#fb923c',
      'Norway': '#94a3b8',
      'Unknown': '#64748b'
    }[s.location || 'Unknown'] || '#64748b';
    
    const sportBadge = s.sport_type === 'kiteboarding'
      ? `<span class="badge" style="background:#06b6d422;color:#06b6d4">🏄 Kite</span>`
      : `<span class="badge" style="background:#8b5cf622;color:#a78bfa">🎿 Snow</span>`;

    const nameHtml = s.activity_name
      ? `<div style="font-weight:600;color:var(--text);font-size:0.82rem;line-height:1.2;">${s.activity_name}</div>
         <div style="font-size:0.71rem;color:var(--text3);margin-top:1px;">${s.date || ''}</div>`
      : `<div style="color:var(--text);">${s.date || '—'}</div>`;

    tr.innerHTML = `
      <td style="color:var(--text3);font-size:0.75rem;">${rank}</td>
      <td>${nameHtml}</td>
      <td>${sportBadge}</td>
      <td><span class="badge" style="background:${locColor}22;color:${locColor}">${s.location || '—'}</span></td>
      <td>${s.duration_min ? s.duration_min.toFixed(0) + ' min' : '—'}</td>
      <td>${distBar}${s.distance_km ? s.distance_km.toFixed(1) + ' km' : '—'}</td>
      <td>${s.avg_speed_kmh ? s.avg_speed_kmh.toFixed(1) + ' km/h' : '—'}</td>
      <td>${spdBar}${s.max_speed_kmh ? '<b>' + s.max_speed_kmh.toFixed(1) + '</b> km/h' : '—'}</td>
    `;
    tr.addEventListener('click', () => selectSession(s));
    tbody.appendChild(tr);
  });
  
  // Sort headers
  document.querySelectorAll('th[data-sort]').forEach(th => {
    const key = th.dataset.sort;
    const arrow = th.querySelector('.sort-arrow');
    th.classList.toggle('sorted', key === sortKey);
    if (arrow) arrow.textContent = key === sortKey ? (sortDir === 1 ? '↓' : '↑') : '';
    th.onclick = () => {
      if (sortKey === key) sortDir *= -1;
      else { sortKey = key; sortDir = 1; }
      updateTable();
    };
  });
}

// ============================================================
// CHARTS
// ============================================================
const CHART_DEFAULTS = {
  responsive: true, maintainAspectRatio: false,
  plugins: { legend: { display: false }, tooltip: { 
    backgroundColor: 'rgba(17,24,39,0.95)', titleColor: '#e2e8f0', bodyColor: '#94a3b8',
    borderColor: '#1e293b', borderWidth: 1, padding: 10, cornerRadius: 8,
    callbacks: {}
  }},
  scales: {
    x: { grid: { color: 'rgba(30,41,59,0.5)' }, ticks: { color: '#64748b', font: { size: 10 } } },
    y: { grid: { color: 'rgba(30,41,59,0.5)' }, ticks: { color: '#64748b', font: { size: 10 } } }
  }
};

function destroyChart(id) { if (charts[id]) { charts[id].destroy(); delete charts[id]; } }

function updateCharts() {
  buildCalendarHeatmap();
  buildMonthlyChart();
  buildSpeedChart();
  buildDistanceChart();
  buildWeeklyVolumeChart();
  buildYearChart();
  buildDowChart();
  buildSpeedZonesChart();
  buildSpeedHistChart();
  buildLocationChart();
  buildPersonalRecords();
}

// ── EWMA utility ─────────────────────────────────────────────────────────────
function computeEWMA(data, alpha) {
  alpha = alpha || 0.18;
  const result = [];
  let ema = null;
  data.forEach(v => {
    if (v == null) { result.push(null); return; }
    ema = ema === null ? v : alpha * v + (1 - alpha) * ema;
    result.push(parseFloat(ema.toFixed(2)));
  });
  return result;
}

function buildMonthlyChart() {
  destroyChart('monthly');

  const MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const years = [...new Set(filteredSessions.map(s => s.year).filter(Boolean))].sort();
  const yearColors = ['#10b981','#06b6d4','#8b5cf6','#f59e0b','#ef4444','#3b82f6','#f97316'];

  // For each year, count sessions by month (1-12)
  const datasets = years.map((yr, i) => {
    const counts = Array(12).fill(0);
    filteredSessions.filter(s => s.year == yr).forEach(s => {
      if (!s.date) return;
      const mo = parseInt(s.date.split('-')[1]) - 1;
      counts[mo]++;
    });
    const col = yearColors[i % yearColors.length];
    return {
      label: String(yr),
      data: counts,
      backgroundColor: col + 'bb',
      borderColor: col,
      borderWidth: 1,
      borderRadius: 3,
      borderSkipped: false
    };
  });

  const ctx = document.getElementById('monthlyChart').getContext('2d');
  charts.monthly = new Chart(ctx, {
    type: 'bar',
    data: { labels: MONTH_NAMES, datasets },
    options: {
      ...JSON.parse(JSON.stringify(CHART_DEFAULTS)),
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: years.length > 1, labels: { color: '#94a3b8', font: { size: 9 }, boxWidth: 12, padding: 8 } },
        tooltip: { backgroundColor: 'rgba(17,24,39,0.95)', bodyColor: '#94a3b8', borderColor: '#1e293b', borderWidth: 1 }
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 10 } } },
        y: { grid: { color: 'rgba(30,41,59,0.5)' }, ticks: { color: '#64748b', font: { size: 10 }, stepSize: 1 } }
      }
    }
  });
}

function buildSpeedChart() {
  destroyChart('speed');
  const s = [...filteredSessions].sort((a,b) => (a.start_timestamp||0)-(b.start_timestamp||0));
  const labels = s.map(x => x.date?.substring(0,10) || '');
  const maxSpdData = s.map(x => x.max_speed_kmh);
  const avgSpdData = s.map(x => x.avg_speed_kmh);
  const ewmaData  = computeEWMA(maxSpdData);

  // Compute cumulative PB at each point (running max)
  let runMax = 0;
  const pbPoints = maxSpdData.map((v, i) => {
    if (v && v > runMax) { runMax = v; return v; }
    return null;
  });

  // Point styling: PB = gold star, normal = small dot
  const pointBgColors = maxSpdData.map((v, i) => pbPoints[i] !== null ? '#f59e0b' : '#ef4444');
  const pointRadii    = maxSpdData.map((v, i) => pbPoints[i] !== null ? 6 : 2.5);
  const pointStyles   = maxSpdData.map((v, i) => pbPoints[i] !== null ? 'star' : 'circle');

  const ctx = document.getElementById('speedChart').getContext('2d');
  charts.speed = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Max Speed', data: maxSpdData,
          borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.08)',
          borderWidth: 1.5, pointRadius: pointRadii, pointHoverRadius: 8,
          pointBackgroundColor: pointBgColors, pointStyle: pointStyles,
          fill: true, tension: 0.3
        },
        {
          label: 'Avg Speed', data: avgSpdData,
          borderColor: '#06b6d4', backgroundColor: 'transparent',
          borderWidth: 1.5, pointRadius: 0, pointHoverRadius: 5,
          fill: false, tension: 0.3, borderDash: [4, 3]
        },
        {
          label: 'EWMA Trend', data: ewmaData,
          borderColor: '#f59e0b', backgroundColor: 'transparent',
          borderWidth: 2.5, pointRadius: 0, pointHoverRadius: 0,
          fill: false, tension: 0.5, borderDash: []
        }
      ]
    },
    options: {
      ...JSON.parse(JSON.stringify(CHART_DEFAULTS)),
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: true, labels: { color: '#94a3b8', font: { size: 10 }, boxWidth: 20, padding: 10 } },
        tooltip: {
          backgroundColor: 'rgba(10,18,35,0.97)', titleColor: '#e2e8f0', bodyColor: '#94a3b8',
          borderColor: '#334155', borderWidth: 1, padding: 10, cornerRadius: 8,
          callbacks: {
            title: items => {
              const sess = s[items[0].dataIndex];
              const pb = pbPoints[items[0].dataIndex] !== null ? ' 🏆 New PB!' : '';
              return (sess?.activity_name || sess?.date || items[0].label) + pb;
            },
            footer: () => '  Click to open session →'
          }
        }
      },
      scales: {
        x: { display: false },
        y: { grid: { color: 'rgba(30,41,59,0.5)' }, ticks: { color: '#64748b', font: {size:10}, callback: v => v + ' km/h' } }
      },
      onClick: (evt, elements) => {
        if (elements.length > 0) selectSession(s[elements[0].index]);
      },
      onHover: (evt, elements) => {
        evt.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
      }
    }
  });
}

function buildDistanceChart() {
  destroyChart('distance');
  const s = [...filteredSessions].sort((a,b) => (a.start_timestamp||0)-(b.start_timestamp||0));
  const ctx = document.getElementById('distanceChart').getContext('2d');
  charts.distance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: s.map(x => x.date?.substring(0,10) || ''),
      datasets: [
        { label: 'Distance (km)', data: s.map(x => x.distance_km), backgroundColor: 'rgba(245,158,11,0.65)', borderColor: '#f59e0b', borderWidth: 1, yAxisID: 'y', borderRadius: 4, hoverBackgroundColor: 'rgba(245,158,11,0.95)' },
        { label: 'Duration (min)', type: 'line', data: s.map(x => x.duration_min), borderColor: '#8b5cf6', backgroundColor: 'transparent', borderWidth: 2, pointRadius: 2, pointHoverRadius: 6, tension: 0.3, yAxisID: 'y2' },
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: true, labels: { color: '#94a3b8', font: { size: 10 }, boxWidth: 20, padding: 10 } },
        tooltip: {
          backgroundColor: 'rgba(10,18,35,0.97)', titleColor: '#e2e8f0', bodyColor: '#94a3b8',
          borderColor: '#334155', borderWidth: 1, padding: 10, cornerRadius: 8,
          callbacks: {
            title: items => s[items[0].dataIndex]?.date || items[0].label,
            footer: () => '  Click to open session →'
          }
        }
      },
      scales: {
        x: { display: false, grid: { display: false } },
        y: { grid: { color: 'rgba(30,41,59,0.5)' }, ticks: { color: '#64748b', font:{size:10}, callback: v => v + ' km' } },
        y2: { position: 'right', grid: { display: false }, ticks: { color: '#64748b', font:{size:10}, callback: v => v + ' min' } }
      },
      onClick: (evt, elements) => {
        if (elements.length > 0) selectSession(s[elements[0].index]);
      },
      onHover: (evt, elements) => {
        evt.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
      }
    }
  });
}

function buildYearChart() {
  destroyChart('year');
  const years = {};
  filteredSessions.forEach(s => { if(s.year) years[s.year] = (years[s.year]||0) + 1; });
  const sortedYears = Object.keys(years).sort();
  const ctx = document.getElementById('yearChart').getContext('2d');
  const colors = ['#8b5cf6','#a78bfa','#7c3aed','#6d28d9','#5b21b6','#4c1d95'];
  charts.year = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: sortedYears,
      datasets: [{ data: sortedYears.map(y => years[y]), backgroundColor: sortedYears.map((_,i) => colors[i%colors.length]+'cc'), borderRadius: 6 }]
    },
    options: {
      ...JSON.parse(JSON.stringify(CHART_DEFAULTS)),
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { backgroundColor: 'rgba(17,24,39,0.95)', bodyColor: '#94a3b8', borderColor: '#1e293b', borderWidth: 1 } },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#94a3b8', font: {size:11} } },
        y: { grid: { color: 'rgba(30,41,59,0.5)' }, ticks: { color: '#64748b', font:{size:10} } }
      }
    }
  });
}

function buildSpeedHistChart() {
  destroyChart('speedHist');
  const speeds = filteredSessions.map(s => s.max_speed_kmh).filter(Boolean);
  if (speeds.length === 0) return;
  
  const bins = [0,15,20,25,30,35,40,45,50,55,60,70,85,100];
  const counts = new Array(bins.length - 1).fill(0);
  speeds.forEach(spd => {
    for (let i = 0; i < bins.length - 1; i++) {
      if (spd >= bins[i] && spd < bins[i+1]) { counts[i]++; break; }
    }
  });
  const labels = bins.slice(0,-1).map((b,i) => `${b}-${bins[i+1]}`);
  const gradient_colors = counts.map((_, i) => {
    const ratio = i / (counts.length - 1);
    const h = 185 - ratio * 165;
    return `hsla(${h}, 80%, 55%, 0.8)`;
  });
  
  const ctx = document.getElementById('speedHistChart').getContext('2d');
  charts.speedHist = new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets: [{ data: counts, backgroundColor: gradient_colors, borderRadius: 4 }] },
    options: {
      ...JSON.parse(JSON.stringify(CHART_DEFAULTS)),
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { backgroundColor: 'rgba(17,24,39,0.95)', bodyColor: '#94a3b8', borderColor: '#1e293b', borderWidth: 1 } },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#64748b', font:{size:9}, maxRotation: 45 } },
        y: { grid: { color: 'rgba(30,41,59,0.5)' }, ticks: { color: '#64748b', font:{size:10} } }
      }
    }
  });
}

function buildDowChart() {
  destroyChart('dow');
  const days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
  const counts = new Array(7).fill(0);
  filteredSessions.forEach(s => {
    if (!s.date) return;
    // Parse date parts manually to avoid UTC/local timezone shift with ISO strings
    const [y, m, d] = s.date.split('-').map(Number);
    const jsDay = new Date(y, m - 1, d).getDay(); // local time, no timezone shift
    const dow = (jsDay + 6) % 7; // Mon=0..Sun=6
    counts[dow]++;
  });
  const ctx = document.getElementById('dowChart').getContext('2d');
  charts.dow = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: days,
      datasets: [{
        data: counts,
        backgroundColor: days.map((_, i) => i >= 5 ? 'rgba(6,182,212,0.8)' : 'rgba(6,182,212,0.35)'),
        borderColor: days.map((_, i) => i >= 5 ? '#06b6d4' : '#06b6d4'),
        borderWidth: 1, borderRadius: 5
      }]
    },
    options: {
      ...JSON.parse(JSON.stringify(CHART_DEFAULTS)),
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { backgroundColor: 'rgba(17,24,39,0.95)', bodyColor: '#94a3b8', borderColor: '#1e293b', borderWidth: 1 } },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#94a3b8', font:{size:11} } },
        y: { grid: { color: 'rgba(30,41,59,0.5)' }, ticks: { color: '#64748b', font:{size:10} } }
      }
    }
  });
}

// ============================================================
// CALENDAR HEATMAP  (Few 2009 – temporal density encoding)
// ============================================================
let calExpandedYears = {};   // year -> bool (expanded)

function calExpandAll() {
  const allYears = [...new Set(filteredSessions.map(s => s.year).filter(Boolean))];
  const anyOpen = allYears.some(y => calExpandedYears[y]);
  allYears.forEach(y => { calExpandedYears[y] = !anyOpen; });
  buildCalendarHeatmap();
}

function toggleCalYear(year) {
  calExpandedYears[year] = !calExpandedYears[year];
  const grid  = document.getElementById('cal-grid-' + year);
  const chev  = document.getElementById('cal-chev-' + year);
  if (grid) grid.classList.toggle('open', !!calExpandedYears[year]);
  if (chev) chev.classList.toggle('open', !!calExpandedYears[year]);
}

function buildCalendarHeatmap() {
  const container = document.getElementById('cal-heatmap');
  if (!container) return;

  const byDate = {};
  filteredSessions.forEach(s => {
    if (!s.date) return;
    if (!byDate[s.date]) byDate[s.date] = { count: 0, dist: 0, sport: s.sport_type, name: s.activity_name || '' };
    byDate[s.date].count++;
    byDate[s.date].dist += (s.distance_km || 0);
    if (s.sport_type === 'snowkiting') byDate[s.date].sport = 'snowkiting';
  });

  const allYears = [...new Set(filteredSessions.map(s => s.year).filter(Boolean))].sort();
  if (!allYears.length) { container.innerHTML = '<div style="color:#475569;font-size:0.8rem;padding:12px;">No sessions.</div>'; return; }

  const allDists   = Object.values(byDate).map(d => d.dist);
  const maxDist    = Math.max(...allDists, 1);
  const MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

  // Automatically expand most recent year (first time)
  const mostRecentYear = allYears[allYears.length - 1];
  if (calExpandedYears[mostRecentYear] === undefined) calExpandedYears[mostRecentYear] = true;

  function getLevel(info) {
    if (!info || !info.dist) return 0;
    const r = info.dist / maxDist;
    if (r < 0.15) return 1;
    if (r < 0.40) return 2;
    if (r < 0.70) return 3;
    return 4;
  }

  function getCellClass(info, level) {
    if (!level) return 'cal-cell level-0';
    return 'cal-cell ' + (info.sport === 'snowkiting' ? 'snow' : 'kite') + '-' + level;
  }

  // Per-month aggregates for compact summary bar
  function monthStats(year) {
    const moCounts = Array(12).fill(0);
    const moDist   = Array(12).fill(0);
    filteredSessions.filter(s => s.year == year && s.date).forEach(s => {
      const mo = parseInt(s.date.split('-')[1]) - 1;
      moCounts[mo]++;
      moDist[mo] += (s.distance_km || 0);
    });
    return { counts: moCounts, dists: moDist };
  }

  let html = '';
  allYears.forEach(year => {
    const ySess = filteredSessions.filter(s => s.year == year);
    if (!ySess.length) return;
    const isOpen = !!calExpandedYears[year];
    const yDist  = ySess.reduce((a, s) => a + (s.distance_km || 0), 0);
    const { counts: moCounts, dists: moDists } = monthStats(year);
    const maxMoDist = Math.max(...moDists, 1);

    // ── Compact summary header ──────────────────────────────
    html += `<div class="cal-year-header" onclick="toggleCalYear(${year})">`;
    html += `<span class="cal-year-chevron${isOpen ? ' open' : ''}" id="cal-chev-${year}">▶</span>`;
    html += `<span class="cal-year-label">${year}</span>`;

    // 12 month mini-blocks
    html += `<div class="cal-month-bar">`;
    for (let mo = 0; mo < 12; mo++) {
      const ratio   = moDists[mo] / maxMoDist;
      const lvl     = moDists[mo] === 0 ? 0 : ratio < 0.25 ? 1 : ratio < 0.5 ? 2 : ratio < 0.75 ? 3 : 4;
      const hasSno  = ySess.filter(s => s.date && parseInt(s.date.split('-')[1])-1 === mo && s.sport_type === 'snowkiting').length > 0;
      const cls     = lvl === 0 ? 'cal-cell level-0' : `cal-cell ${hasSno ? 'snow' : 'kite'}-${lvl}`;
      const tip     = moCounts[mo] > 0 ? `${MONTH_NAMES[mo]}: ${moCounts[mo]} session${moCounts[mo]>1?'s':''}, ${moDists[mo].toFixed(0)} km` : MONTH_NAMES[mo];
      html += `<div class="${cls} cal-mo-block" style="cursor:default;border-radius:3px;" title="${tip}"></div>`;
    }
    html += `</div>`;
    html += `<span class="cal-year-meta">${ySess.length} sessions · ${yDist.toFixed(0)} km</span>`;
    html += `</div>`;

    // ── Full heatmap grid (collapsible) ──────────────────────
    html += `<div class="cal-year-grid${isOpen ? ' open' : ''}" id="cal-grid-${year}">`;
    html += `<div class="cal-year-grid-inner">`;
    html += `<div style="display:flex;gap:2px;align-items:flex-start;">`;

    // Day-of-week labels
    html += `<div style="display:flex;flex-direction:column;gap:2px;padding-top:18px;margin-right:3px;">`;
    ['M','','W','','F','','S'].forEach(lbl => {
      html += `<div style="height:11px;font-size:0.5rem;color:#475569;text-align:right;padding-right:2px;line-height:11px;margin-bottom:2px;">${lbl}</div>`;
    });
    html += `</div>`;

    // Build weeks
    const jan1    = new Date(year, 0, 1);
    const j1Dow   = jan1.getDay() === 0 ? 7 : jan1.getDay();
    const startDt = new Date(year, 0, 1 - (j1Dow - 1));
    const dec31   = new Date(year, 11, 31);
    const d31Dow  = dec31.getDay() === 0 ? 7 : dec31.getDay();
    const endDt   = new Date(year, 11, 31 + (7 - d31Dow));

    const weeks = [];
    const cur   = new Date(startDt);
    while (cur <= endDt) {
      const week = [];
      for (let d = 0; d < 7; d++) { week.push(new Date(cur)); cur.setDate(cur.getDate() + 1); }
      weeks.push(week);
    }

    html += `<div style="display:flex;flex-direction:column;gap:1px;">`;
    // Month labels row
    html += `<div style="display:flex;gap:2px;height:15px;margin-bottom:2px;">`;
    let lastLabelMo = -1;
    weeks.forEach(week => {
      const firstInYear = week.find(d => d.getFullYear() == year);
      const mo          = firstInYear ? firstInYear.getMonth() : -1;
      if (mo !== -1 && mo !== lastLabelMo) { lastLabelMo = mo; html += `<div style="width:11px;font-size:0.55rem;color:#64748b;white-space:nowrap;overflow:visible;">${MONTH_NAMES[mo]}</div>`; }
      else { html += `<div style="width:11px;"></div>`; }
    });
    html += `</div>`;

    // Week columns
    html += `<div style="display:flex;gap:2px;">`;
    weeks.forEach(week => {
      html += `<div style="display:flex;flex-direction:column;gap:2px;">`;
      week.forEach(dt => {
        if (dt.getFullYear() != year) { html += `<div style="width:11px;height:11px;"></div>`; return; }
        const ds   = `${dt.getFullYear()}-${String(dt.getMonth()+1).padStart(2,'0')}-${String(dt.getDate()).padStart(2,'0')}`;
        const info = byDate[ds];
        const lv   = getLevel(info);
        const cls  = getCellClass(info, lv);
        const tip  = info ? `${ds}\n${info.dist.toFixed(1)} km · ${info.count} session${info.count>1?'s':''}`  + (info.name ? `\n${info.name}` : '') : ds;
        html += `<div class="${cls}" style="width:11px;height:11px;" title="${tip}" onclick="openCalDay('${ds}')"></div>`;
      });
      html += `</div>`;
    });
    html += `</div></div></div></div></div>`;  // close week cols, flex-col, inner, grid
  });

  container.innerHTML = html;
}


function openCalDay(dateStr) {
  const sess = filteredSessions.filter(s => s.date === dateStr);
  if (sess.length === 1) selectSession(sess[0]);
  else if (sess.length > 1) {
    // Multiple sessions on same day – open first
    selectSession(sess[0]);
  }
}

// ============================================================
// WEEKLY TRAINING VOLUME  (Banister/Foster training load model)
// ============================================================
function buildWeeklyVolumeChart() {
  destroyChart('weeklyVol');
  const weeklyDist = {};
  filteredSessions.forEach(s => {
    if (!s.date) return;
    const wk = getISOWeekKey(s.date);
    weeklyDist[wk] = (weeklyDist[wk] || 0) + (s.distance_km || 0);
  });
  const sorted = Object.keys(weeklyDist).sort();
  if (sorted.length === 0) return;
  const vals = sorted.map(w => parseFloat(weeklyDist[w].toFixed(1)));

  // 4-week rolling average (chronic load baseline)
  const rolling4 = vals.map((_, i) => {
    const slice = vals.slice(Math.max(0, i - 3), i + 1);
    return parseFloat((slice.reduce((a, b) => a + b, 0) / slice.length).toFixed(1));
  });

  // Human-readable week labels: show month only on first week of each month
  const labels = sorted.map(wk => {
    // wk = "2023-W05" – parse back to approximate date
    const [yr, wPart] = wk.split('-W');
    const weekNum = parseInt(wPart);
    const jan4 = new Date(parseInt(yr), 0, 4);
    const startOfW1 = new Date(jan4);
    startOfW1.setDate(jan4.getDate() - ((jan4.getDay() + 6) % 7));
    const d = new Date(startOfW1);
    d.setDate(d.getDate() + (weekNum - 1) * 7);
    const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return d.getDate() === 1 || d.getDate() <= 7
      ? MONTHS[d.getMonth()] + " '" + String(d.getFullYear()).slice(2)
      : '';
  });

  const ctx = document.getElementById('weeklyVolChart');
  if (!ctx) return;
  charts.weeklyVol = new Chart(ctx.getContext('2d'), {
    type: 'bar',
    data: {
      labels: sorted,
      datasets: [
        {
          label: 'Weekly km', data: vals,
          backgroundColor: vals.map(v => v > 0 ? 'rgba(245,158,11,0.45)' : 'transparent'),
          borderColor: '#f59e0b', borderWidth: 1, borderRadius: 3, order: 2
        },
        {
          label: '4-week rolling avg', type: 'line', data: rolling4,
          borderColor: '#06b6d4', backgroundColor: 'transparent',
          borderWidth: 2.5, pointRadius: 0, tension: 0.45, order: 1
        }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: true, labels: { color: '#94a3b8', font: { size: 10 }, boxWidth: 16, padding: 10 } },
        tooltip: {
          backgroundColor: 'rgba(10,18,35,0.97)', bodyColor: '#94a3b8',
          borderColor: '#334155', borderWidth: 1, padding: 10, cornerRadius: 8,
          callbacks: {
            title: items => 'Week of ' + (() => {
              const wk = sorted[items[0].dataIndex];
              const [yr, wPart] = wk.split('-W');
              const weekNum = parseInt(wPart);
              const jan4 = new Date(parseInt(yr), 0, 4);
              const s0 = new Date(jan4);
              s0.setDate(jan4.getDate() - ((jan4.getDay() + 6) % 7));
              const d = new Date(s0); d.setDate(d.getDate() + (weekNum - 1) * 7);
              const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
              return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
            })(),
            label: item => item.datasetIndex === 0
              ? `  Weekly: ${item.parsed.y} km`
              : `  4-wk avg: ${item.parsed.y} km`
          }
        }
      },
      scales: {
        x: {
          display: true, grid: { display: false },
          ticks: {
            color: '#475569', font: { size: 9 }, maxRotation: 0,
            callback: (val, i) => labels[i] || ''
          }
        },
        y: {
          grid: { color: 'rgba(30,41,59,0.5)' },
          ticks: { color: '#64748b', font: { size: 10 }, callback: v => v + ' km' }
        }
      }
    }
  });
}

// ============================================================
// SPEED ZONES  (standard kite/action-sports zone model)
// ============================================================
function buildSpeedZonesChart() {
  destroyChart('zones');
  const ZONES = [
    { label: '< 20 km/h',   min: 0,  max: 20,  color: '#06b6d4' },
    { label: '20 – 30',     min: 20, max: 30,  color: '#0ea5e9' },
    { label: '30 – 40',     min: 30, max: 40,  color: '#f59e0b' },
    { label: '40 – 50',     min: 40, max: 50,  color: '#ef4444' },
    { label: '50+ km/h',    min: 50, max: 9999, color: '#8b5cf6' }
  ];

  const counts = ZONES.map(z =>
    filteredSessions.filter(s => {
      const v = s.max_speed_kmh;
      return v != null && v >= z.min && v < z.max;
    }).length
  );

  if (counts.every(c => c === 0)) return;
  const ctx = document.getElementById('zonesChart');
  if (!ctx) return;

  charts.zones = new Chart(ctx.getContext('2d'), {
    type: 'doughnut',
    data: {
      labels: ZONES.map(z => z.label),
      datasets: [{
        data: counts,
        backgroundColor: ZONES.map(z => z.color + 'cc'),
        borderColor: ZONES.map(z => z.color),
        borderWidth: 1.5,
        hoverOffset: 8
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      cutout: '62%',
      plugins: {
        legend: {
          display: true, position: 'right',
          labels: { color: '#94a3b8', font: { size: 10 }, padding: 8, boxWidth: 12 }
        },
        tooltip: {
          backgroundColor: 'rgba(10,18,35,0.97)', bodyColor: '#94a3b8',
          borderColor: '#334155', borderWidth: 1, padding: 10, cornerRadius: 8,
          callbacks: {
            label: item => {
              const total = counts.reduce((a, b) => a + b, 0);
              const pct = total > 0 ? (item.parsed / total * 100).toFixed(1) : 0;
              return `  ${item.parsed} sessions (${pct}%)`;
            }
          }
        }
      }
    }
  });
}

// ============================================================
// PERSONAL RECORDS  (all-time bests, clickable to open session)
// ============================================================
function buildPersonalRecords() {
  const el = document.getElementById('personal-records');
  if (!el) return;
  if (filteredSessions.length === 0) { el.innerHTML = ''; return; }

  function bestBy(field, label, icon, fmt, color) {
    const valid = filteredSessions.filter(s => s[field] != null && s[field] > 0);
    if (!valid.length) return null;
    valid.sort((a, b) => b[field] - a[field]);
    const s = valid[0];
    return { sess: s, field, label, icon, val: fmt(s[field]), sub: s.location || '', color };
  }
  function bestByMin(field, label, icon, fmt, color) {
    const valid = filteredSessions.filter(s => s[field] != null && s[field] > -999);
    if (!valid.length) return null;
    valid.sort((a, b) => a[field] - b[field]);
    const s = valid[0];
    return { sess: s, field, label, icon, val: fmt(s[field]), sub: s.location || '', color };
  }

  const records = [
    bestBy('max_speed_kmh',  'Fastest Speed',     '⚡',   v => v.toFixed(1) + ' km/h', '#ef4444'),
    bestBy('distance_km',    'Longest Distance',  '📏',   v => v.toFixed(1) + ' km',   '#10b981'),
    bestBy('duration_min',   'Longest Duration',  '⏱',   v => { const h=Math.floor(v/60),m=Math.round(v%60); return h>0?`${h}h ${m}m`:`${m} min`; }, '#06b6d4'),
    bestBy('avg_speed_kmh',  'Best Avg Speed',    '🚀',   v => v.toFixed(1) + ' km/h', '#f59e0b'),
    bestBy('calories',       'Most Calories',     '🔥',   v => Math.round(v) + ' kcal', '#f97316'),
    bestBy('avg_alt',        'Highest Altitude',  '🏔',   v => Math.round(v) + ' m',   '#8b5cf6'),
    bestByMin('avg_temp',    'Coldest Session',   '🥶',   v => v + '°C',               '#3b82f6'),
  ].filter(Boolean);

  el.innerHTML = records.map(r => {
    const date = r.sess.date || '';
    const name = r.sess.activity_name || date;
    return `<div class="pr-card" style="border-top:2px solid ${r.color}20;" onclick="selectSession(ALL_SESSIONS.find(s=>s.filename==='${r.sess.filename}'))">
      <div class="pr-card-icon">${r.icon}</div>
      <div class="pr-card-label">${r.label}</div>
      <div class="pr-card-val" style="color:${r.color}">${r.val}</div>
      <div class="pr-card-sub">${r.sub}</div>
      <div class="pr-card-name">${name}</div>
    </div>`;
  }).join('');
}

// ============================================================
// LOCATION LEADERBOARD  (sessions + km per spot)
// ============================================================
function buildLocationChart() {
  destroyChart('location');
  const locStats = {};
  filteredSessions.forEach(s => {
    const loc = s.location || 'Unknown';
    if (!locStats[loc]) locStats[loc] = { sessions: 0, dist: 0 };
    locStats[loc].sessions++;
    locStats[loc].dist += (s.distance_km || 0);
  });

  // Sort by session count, take top 10
  const sorted = Object.entries(locStats)
    .sort((a, b) => b[1].sessions - a[1].sessions)
    .slice(0, 10);

  if (!sorted.length) return;
  const labels   = sorted.map(([loc]) => loc);
  const sessions = sorted.map(([, v]) => v.sessions);
  const dists    = sorted.map(([, v]) => parseFloat(v.dist.toFixed(0)));

  const ctx = document.getElementById('locationChart');
  if (!ctx) return;

  charts.location = new Chart(ctx.getContext('2d'), {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Sessions', data: sessions, backgroundColor: 'rgba(6,182,212,0.6)', borderColor: '#06b6d4', borderWidth: 1, borderRadius: 4, yAxisID: 'y', order: 2 },
        { label: 'Distance (km)', type: 'line', data: dists, borderColor: '#f59e0b', backgroundColor: 'transparent', borderWidth: 2.5, pointRadius: 4, pointHoverRadius: 7, tension: 0.3, yAxisID: 'y2', order: 1 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: true, labels: { color: '#94a3b8', font: { size: 10 }, boxWidth: 14, padding: 10 } },
        tooltip: {
          backgroundColor: 'rgba(10,18,35,0.97)', bodyColor: '#94a3b8',
          borderColor: '#334155', borderWidth: 1, padding: 10, cornerRadius: 8
        }
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 9 }, maxRotation: 30 } },
        y: {
          grid: { color: 'rgba(30,41,59,0.5)' },
          ticks: { color: '#64748b', font: { size: 10 }, stepSize: 1 },
          title: { display: true, text: 'Sessions', color: '#475569', font: { size: 9 } }
        },
        y2: {
          position: 'right', grid: { display: false },
          ticks: { color: '#64748b', font: { size: 10 }, callback: v => v + ' km' },
          title: { display: true, text: 'km', color: '#475569', font: { size: 9 } }
        }
      }
    }
  });
}
</script>
</body>
</html>'''

if __name__ == "__main__":
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kite_dashboard.html')
    with open(out_path, 'w') as f:
        f.write(html)
    print(f"Dashboard written: {os.path.getsize(out_path)/1024:.0f} KB")
