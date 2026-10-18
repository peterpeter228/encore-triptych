"""Triptych Alpha: private, read-only Web3 research workbench."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import sys
import threading
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
from starlette.concurrency import run_in_threadpool

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'vendor'))
MAX_BODY_BYTES = 256 * 1024
FRESHNESS_SECONDS = 300
LOGGER = logging.getLogger('triptych-alpha')


def now():
    return datetime.now(timezone.utc).isoformat()


def collect_live(cache_dir, force=False):
    from radar.live import collect_live as collect
    return collect(cache_dir, force=force)


def business():
    from radar import business as module
    return module


def analyzed_cards(signals):
    """Join only exact protocol identities; two metrics are not two independent sources."""
    groups = {}
    for signal in signals:
        url = signal.get('url', '')
        chains = signal.get('chains')
        if (signal.get('source_id') in ('defillama_fees', 'defillama_revenue')
                and isinstance(url, str) and url.startswith('https://defillama.com/protocol/')
                and isinstance(chains, list) and chains and all(isinstance(c, str) for c in chains)):
            groups.setdefault((url, tuple(sorted(chains))), []).append(signal)
    merged_by_id = {}
    consumed = set()
    for (url, chains), rows in groups.items():
        # Ambiguous duplicates are deliberately not merged.
        if len(rows) != 2 or {r['source_id'] for r in rows} != {'defillama_fees', 'defillama_revenue'}:
            continue
        ordered = sorted(rows, key=lambda r: r['source_id'])
        merged = deepcopy(ordered[0])
        merged.update(id='protocol-' + hashlib.sha256((url + '|' + '|'.join(chains)).encode()).hexdigest()[:24],
                      source_id='defillama_combined', source_ids=[r['source_id'] for r in ordered],
                      metrics_type='protocol_metrics', source_refs=list(dict.fromkeys(r['url'] for r in ordered)),
                      evidence_note='Fee and revenue observations from the same provider, not independent corroboration.',
                      metrics={'net_profit_usd': None}, per_metric_provenance={})
        for row in ordered:
            kind = 'fees' if row['source_id'] == 'defillama_fees' else 'revenue'
            for key, value in row.get('metrics', {}).items():
                if key.startswith(kind + '_') or key == 'change_7d_percent':
                    typed_key = kind + '_change_7d_percent' if key == 'change_7d_percent' else key
                    merged['metrics'][typed_key] = value
                    merged['per_metric_provenance'][typed_key] = {
                        'source_id': row['source_id'], 'observed_at': row.get('observed_at'),
                        'evidence_status': row.get('evidence_status'), 'url': row.get('url')}
        freshness = {'fresh': 0, 'cached': 1, 'stale': 2, 'unverified': 3}
        merged['evidence_status'] = max((r.get('evidence_status', 'unverified') for r in ordered),
                                       key=lambda value: freshness.get(value, 3))
        times = [r.get('observed_at') for r in ordered if r.get('observed_at')]
        merged['observed_at'] = min(times) if len(times) == len(ordered) else None
        merged_by_id[rows[0]['id']] = merged
        consumed.update(r['id'] for r in rows[1:])
    cards = []
    for raw in signals:
        if raw['id'] in consumed:
            continue
        signal = merged_by_id.get(raw['id'], raw)
        card = business().analyze_signal(signal)
        card.update({key: signal.get(key) for key in (
            'name', 'category', 'chain', 'chains', 'source_id', 'evidence_status', 'observed_at', 'metrics_type')})
        for key in ('source_ids', 'per_metric_provenance', 'evidence_note'):
            if key in signal:
                card[key] = deepcopy(signal[key])
        cards.append(card)
    return cards


class ScanRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    force: bool = False


def create_app(data_dir=None):
    data = Path(data_dir or os.environ.get('TRIPTYCH_ALPHA_DATA_DIR', ROOT / 'alpha-data'))
    data.mkdir(parents=True, exist_ok=True)
    cache = data / 'cache'
    cache.mkdir(exist_ok=True)
    dbpath = data / 'alpha.sqlite3'
    scan_lock = threading.Lock()
    status_lock = threading.Lock()
    status = {'mode': 'private_research', 'scan_running': False, 'last_error': None,
              'last_attempt_at': None, 'paid_budget_usd': 0, 'transactions_enabled': False}

    @contextmanager
    def db():
        con = sqlite3.connect(dbpath, timeout=15)
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    with db() as con:
        con.execute('CREATE TABLE IF NOT EXISTS snapshots (id INTEGER PRIMARY KEY CHECK (id=1), payload TEXT NOT NULL)')
        con.execute('CREATE TABLE IF NOT EXISTS scan_runs (run_id TEXT PRIMARY KEY, attempted_at TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL)')
        con.execute('CREATE TABLE IF NOT EXISTS imports (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)')

    app = FastAPI(title='Triptych Alpha · Private Research', docs_url=None, redoc_url=None, openapi_url=None)
    app.state.data_dir = data

    @app.middleware('http')
    async def security(request: Request, call_next):
        try:
            host = urlsplit('http://' + request.headers.get('host', '')).hostname
            # Access is only supported from a loopback listener. Reject DNS rebinding.
            if host not in ('127.0.0.1', 'localhost', '::1'):
                return JSONResponse({'detail': 'Local access only'}, status_code=403)
            origin = request.headers.get('origin')
            if origin and origin != str(request.base_url).rstrip('/'):
                return JSONResponse({'detail': 'Cross-origin access denied'}, status_code=403)
            if request.headers.get('sec-fetch-site') == 'cross-site':
                return JSONResponse({'detail': 'Cross-site access denied'}, status_code=403)
            length = request.headers.get('content-length')
            if length is not None and (int(length) < 0 or int(length) > MAX_BODY_BYTES):
                return JSONResponse({'detail': 'Request exceeds 256 KiB'}, status_code=413)
        except ValueError:
            return JSONResponse({'detail': 'Invalid request headers'}, status_code=400)
        if request.method in ('POST', 'PUT', 'PATCH'):
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > MAX_BODY_BYTES:
                    return JSONResponse({'detail': 'Request exceeds 256 KiB'}, status_code=413)
            request._body = bytes(body)
        response = await call_next(request)
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; "
            "connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response.headers['Cache-Control'] = 'no-store'
        return response

    def state():
        with db() as con:
            row = con.execute('SELECT payload FROM snapshots WHERE id=1').fetchone()
            imports = [json.loads(r[0]) for r in con.execute('SELECT payload FROM imports ORDER BY created_at DESC LIMIT 100')]
        snapshot = json.loads(row[0]) if row else {'scan': None, 'cards': []}
        with status_lock:
            current_status = dict(status)
        # Compute freshness on returned copies, never rewrite historical observation times.
        current = datetime.now(timezone.utc)
        def age(timestamp):
            try:
                stamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                if stamp.tzinfo is None:
                    return None
                return max(0, (current - stamp).total_seconds())
            except (ValueError, TypeError, AttributeError):
                return None
        scan = snapshot.get('scan')
        current_status['scan_age_seconds'] = age(scan.get('observed_at')) if scan else None
        if scan:
            source_health = {}
            for source in scan.get('sources', []):
                source_age = age(source.get('fetched_at'))
                source['current_age_seconds'] = source_age
                if source.get('status') in ('success', 'cached') and (source_age is None or source_age > FRESHNESS_SECONDS):
                    source['observation_status'] = source['status']
                    source['status'] = 'stale'
                    source['freshness_reason'] = 'Stored observation is beyond the five-minute freshness window.'
                source_health[source.get('id')] = source.get('status')
            for signal in scan.get('signals', []) + snapshot.get('cards', []):
                source_status = source_health.get(signal.get('source_id'))
                combined_states = [source_health.get(sid) for sid in signal.get('source_ids', [])]
                if 'stale' in combined_states:
                    source_status = 'stale'
                elif combined_states and all(item in ('success', 'cached') for item in combined_states):
                    source_status = 'cached' if 'cached' in combined_states else 'success'
                for metric in signal.get('per_metric_provenance', {}).values():
                    if source_health.get(metric.get('source_id')) == 'stale':
                        metric['evidence_status'] = 'stale'
                observation_age = age(signal.get('observed_at'))
                if source_status == 'stale' or (source_status is None and
                        (observation_age is None or observation_age > FRESHNESS_SECONDS)):
                    signal['evidence_status'] = 'stale'
        return {**snapshot, 'imports': imports, 'status': current_status}

    def opportunity(oid):
        current = state()
        for card in current['cards'] + current['imports']:
            if card.get('id') == oid:
                return card
        raise HTTPException(404, 'Opportunity not found')

    @app.get('/api/health')
    def health():
        return {'ok': True, 'service': 'Triptych Alpha', 'mode': 'private_research', 'transactions_enabled': False}

    @app.get('/api/state')
    def get_state():
        return state()

    @app.get('/api/runs')
    def runs():
        with db() as con:
            rows = con.execute('SELECT run_id,attempted_at,status,payload FROM scan_runs ORDER BY rowid DESC LIMIT 100').fetchall()
        summaries = []
        for rid, attempted, run_status, encoded in rows:
            payload = json.loads(encoded)
            scan = payload.get('scan') or {}
            summaries.append({'run_id': rid, 'attempted_at': attempted, 'status': run_status,
                              'collector_run_id': scan.get('run_id'), 'signal_count': len(scan.get('signals', [])),
                              'sources': [{'id': source.get('id'), 'status': source.get('status'),
                                           'fetched_at': source.get('fetched_at')} for source in scan.get('sources', [])]})
        return {'runs': summaries, 'limit': 100}

    @app.get('/api/runs/{run_id}')
    def get_run(run_id: str):
        with db() as con:
            row = con.execute('SELECT attempted_at,status,payload FROM scan_runs WHERE run_id=?', (run_id,)).fetchone()
        if not row:
            raise HTTPException(404, 'Run not found')
        return {'run_id': run_id, 'attempted_at': row[0], 'status': row[1], **json.loads(row[2])}

    def record_run(con, rid, attempted, run_status, payload):
        # Never replace historical evidence, even if a faulty collector reuses a run ID.
        if con.execute('SELECT 1 FROM scan_runs WHERE run_id=?', (rid,)).fetchone():
            rid = str(uuid4())
        con.execute('INSERT INTO scan_runs(run_id,attempted_at,status,payload) VALUES(?,?,?,?)',
                    (rid, attempted, run_status, json.dumps(payload, ensure_ascii=False, allow_nan=False)))

    def run_scan(force):
        if not scan_lock.acquire(blocking=False):
            raise HTTPException(409, 'A scan is already running')
        attempted = now()
        rid = str(uuid4())
        bundle = None
        try:
            with status_lock:
                status.update(scan_running=True, last_attempt_at=attempted, last_error=None)
            bundle = collect_live(cache, force=force)
            if not isinstance(bundle, dict) or not isinstance(bundle.get('signals'), list) or not isinstance(bundle.get('sources'), list):
                raise ValueError('Invalid collector bundle')
            if isinstance(bundle.get('run_id'), str) and 0 < len(bundle['run_id']) <= 100:
                rid = bundle['run_id']
            cards = analyzed_cards(bundle['signals'])
            snapshot = {'scan': bundle, 'cards': cards}
            encoded = json.dumps(snapshot, ensure_ascii=False, allow_nan=False)
            source_states = [source.get('status') for source in bundle['sources']]
            run_status = ('success' if source_states and all(item in ('success', 'cached') for item in source_states)
                          else 'partial' if any(item in ('success', 'cached', 'stale') for item in source_states) else 'error')
            with db() as con:
                record_run(con, rid, attempted, run_status, {'scan': bundle})
                con.execute('INSERT INTO snapshots(id,payload) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload', (encoded,))
        except HTTPException:
            raise
        except Exception:
            LOGGER.exception('Scan failed; previous persisted snapshot retained')
            with status_lock:
                status['last_error'] = 'Scan failed. Previous observation retained; no synthetic fallback was used.'
            try:
                with db() as con:
                    record_run(con, rid, attempted, 'error', {'scan': bundle, 'error': status['last_error']})
            except Exception:
                LOGGER.exception('Could not persist failure history')
            raise HTTPException(502, status['last_error'])
        finally:
            with status_lock:
                status['scan_running'] = False
            scan_lock.release()
        return state()

    @app.post('/api/scan')
    async def scan(body: ScanRequest):
        return await run_in_threadpool(run_scan, body.force)

    @app.get('/api/opportunities/{oid}')
    def get_opportunity(oid: str):
        return opportunity(oid)

    @app.post('/api/scenario')
    def scenario(body: dict):
        try:
            return business().scenario(**body)
        except (ValueError, TypeError, KeyError) as exc:
            raise HTTPException(422, str(exc)[:500]) from exc

    @app.get('/api/opportunities/{oid}/spec')
    def spec(oid: str):
        card = opportunity(oid)
        document = business().export_spec(card)
        return Response(document, media_type='text/markdown; charset=utf-8', headers={
            'Content-Disposition': 'attachment; filename="TRIPTYCH_ALPHA_BUILD_SPEC.md"'})

    @app.post('/api/muse/ingest', status_code=201)
    def ingest(body: dict):
        try:
            validated = business().validate_muse_import(body)
            imported = business().analyze_signal(validated)
            imported['original_import'] = validated
        except (ValueError, TypeError, KeyError) as exc:
            raise HTTPException(422, str(exc)[:500]) from exc
        # Imported claims never become verified live source observations or executable instructions.
        encoded = json.dumps(imported, ensure_ascii=False, allow_nan=False)
        iid = 'muse-' + hashlib.sha256(encoded.encode()).hexdigest()[:24]
        imported['id'] = iid
        imported['evidence_status'] = 'unverified'
        imported['imported_at'] = now()
        with db() as con:
            con.execute('INSERT INTO imports(id,created_at,payload) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',
                        (iid, now(), json.dumps(imported, ensure_ascii=False, allow_nan=False)))
        return {'import': imported, 'status': 'unverified', 'actions_executed': 0}

    @app.get('/')
    def index():
        return FileResponse(ROOT / 'static' / 'index.html')

    app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')
    return app


app = create_app()

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=int(os.environ.get('PORT', '8765')), proxy_headers=False)
