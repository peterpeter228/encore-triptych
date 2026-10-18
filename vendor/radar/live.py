"""Bounded, credential-free public observations. Never modifies the evidence ledger."""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path
import socket
import tempfile
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, parse_qsl
from urllib.request import Request, HTTPRedirectHandler, build_opener
from uuid import uuid4

SCHEMA_VERSION = '1.0'
CACHE_SECONDS = 300
TIMEOUT_SECONDS = 12
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_SIGNALS = 60
# Category selection is a research scope, not proof of low risk or buildability.
LIGHTWEIGHT_CATEGORIES = frozenset({
    'trading app', 'trading terminal', 'dex aggregator', 'dex aggregators',
    'launchpad', 'nft launchpad', 'yield aggregator', 'nft marketplace',
    'interface', 'telegram bot', 'wallet', 'wallets', 'analytics',
    'portfolio tracker', 'coins tracker', 'consumer', 'consumer app',
    'ai agents', 'developer tools', 'payments', 'identity & reputation', 'dca tools',
})
PRIMARY_CHAINS = ('solana', 'base', 'avalanche', 'ethereum', 'arbitrum', 'optimism')
_LLAMA = 'https://api.llama.fi/overview/fees?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true&dataType='
SOURCES = (
    {'id': 'defillama_fees', 'url': _LLAMA + 'dailyFees', 'limit': 20},
    {'id': 'defillama_revenue', 'url': _LLAMA + 'dailyRevenue', 'limit': 20},
    {'id': 'dexscreener_boosts', 'url': 'https://api.dexscreener.com/token-boosts/top/v1', 'limit': 10},
    {'id': 'dexscreener_profiles', 'url': 'https://api.dexscreener.com/token-profiles/latest/v1', 'limit': 10},
    {'id': 'superteam_listings', 'url': 'https://superteam.fun/api/agents/listings/live?take=20', 'limit': 0},
)
ALLOWED_URLS = frozenset(s['url'] for s in SOURCES)


def _iso(epoch=None):
    return datetime.fromtimestamp(time.time() if epoch is None else epoch, timezone.utc).isoformat().replace('+00:00', 'Z')


def _number(value):
    return value if type(value) in (int, float) and math.isfinite(value) else None


def _text(value, limit=240):
    return value[:limit] if isinstance(value, str) else None


def _safe_url(value):
    if not isinstance(value, str) or len(value) > 2048 or any(ord(c) <= 32 for c in value):
        return None
    try:
        p = urlsplit(value)
        host = p.hostname
        if p.scheme != 'https' or not host or p.username or p.password:
            return None
        if host.lower().endswith(('.localhost', '.local', '.internal')) or host.lower() == 'localhost':
            return None
        try:
            if not ipaddress.ip_address(host).is_global:
                return None
        except ValueError:
            if '.' not in host or all(c.isdigit() or c == '.' for c in host):
                return None
        secret_keys = {'api_key', 'apikey', 'key', 'token', 'access_token', 'secret',
                       'password', 'authorization', 'signature', 'sig'}
        if any(k.lower() in secret_keys for k, _ in parse_qsl(p.query)):
            return None
        return value
    except ValueError:
        return None


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('redirect_refused')


def _fetch_json(url):
    """No API keys, redirects, retries, or caller-supplied destinations."""
    if url not in ALLOWED_URLS:
        raise ValueError('endpoint_not_allowlisted')
    request = Request(url, headers={'Accept': 'application/json', 'Accept-Encoding': 'identity',
                                    'User-Agent': 'Web3ResearchRadar/1.0'})
    start = time.monotonic()
    with build_opener(_NoRedirect()).open(request, timeout=TIMEOUT_SECONDS) as response:
        size = response.headers.get('Content-Length')
        if size and int(size) > MAX_RESPONSE_BYTES:
            raise ValueError('response_too_large')
        data = bytearray()
        while True:
            if time.monotonic() - start > TIMEOUT_SECONDS:
                raise TimeoutError('response_deadline_exceeded')
            chunk = response.read(min(65536, MAX_RESPONSE_BYTES + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > MAX_RESPONSE_BYTES:
                raise ValueError('response_too_large')
    return json.loads(data)


def _normalize(source, payload, stats=None):
    sid = source['id']
    llama = sid.startswith('defillama')
    if llama:
        if not isinstance(payload, dict) or not isinstance(payload.get('protocols'), list):
            raise ValueError('schema_mismatch_expected_protocols_array')
        rows = payload['protocols']
    else:
        if not isinstance(payload, list):
            raise ValueError('schema_mismatch_expected_array')
        rows = payload
    if stats is None:
        stats = {}
    stats.update(input_count=len(rows), excluded_count=0, non_primary_chain_count=0,
                 malformed_count=0, duplicate_count=0, primary_count=0, unknown_category_count=0)
    result = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            stats['malformed_count'] += 1
            continue
        raw_chains = row.get('chains', []) if llama else [row.get('chainId')]
        if not isinstance(raw_chains, list):
            stats['malformed_count'] += 1
            continue
        chains = sorted(set(c.lower() for c in raw_chains if isinstance(c, str)))
        chains = ['avalanche' if c == 'avax' else c for c in chains]
        if not set(chains).intersection(PRIMARY_CHAINS):
            stats['non_primary_chain_count'] += 1
            continue
        provider_category = _text(row.get('category')) if llama else None
        category_key = provider_category.strip().lower() if provider_category else None
        if llama and category_key and category_key not in LIGHTWEIGHT_CATEGORIES:
            stats['excluded_count'] += 1
            continue
        identity = (row.get('slug') or row.get('defillamaId') or row.get('name')) if llama else row.get('tokenAddress')
        if not isinstance(identity, (str, int)) or isinstance(identity, bool):
            stats['malformed_count'] += 1
            continue
        key = str(identity) + ':' + ','.join(chains)
        if key in seen:
            stats['duplicate_count'] += 1
            continue
        seen.add(key)
        metrics = dict.fromkeys(('fees_24h_usd', 'revenue_24h_usd', 'fees_7d_usd', 'revenue_7d_usd',
                                 'change_7d_percent', 'boost_amount', 'boost_total_amount', 'net_profit_usd'))
        if llama:
            kind = 'fees' if sid.endswith('fees') else 'revenue'
            metrics[kind + '_24h_usd'] = _number(row.get('total24h'))
            metrics[kind + '_7d_usd'] = _number(row.get('total7d'))
            metrics['change_7d_percent'] = _number(row.get('change_7d'))
            # Do not replace change_7d with change_1d or infer growth from cumulative amounts.
            slug = _text(row.get('slug'))
            url = 'https://defillama.com/protocol/' + slug if slug and all(c.isalnum() or c in '-_' for c in slug) else source['url']
            category = provider_category if category_key else None
            name = _text(row.get('name')) or str(identity)[:240]
        else:
            kind = 'paid_promotion' if sid.endswith('boosts') else 'token_profile'
            metrics['boost_amount'] = _number(row.get('amount')) if kind == 'paid_promotion' else None
            metrics['boost_total_amount'] = _number(row.get('totalAmount')) if kind == 'paid_promotion' else None
            url = _safe_url(row.get('url')) or source['url']
            category = kind
            name = _text(row.get('name')) or str(identity)[:240]
        tier = 'unknown_category_secondary' if llama and not category_key else 'primary'
        stats['unknown_category_count' if tier == 'unknown_category_secondary' else 'primary_count'] += 1
        result.append({
            'selection_tier': tier,
            'id': sid + ':' + hashlib.sha256(key.encode()).hexdigest()[:20],
            'name': name, 'chain': chains[0] if len(chains) == 1 else 'multichain', 'chains': chains,
            'category': category, 'source_id': sid, 'url': url, 'metrics': metrics,
            'metrics_type': kind, 'metric_scope': 'protocol_all_chains' if llama else 'token',
            'time_window': 'provider_reported_24h_and_7d' if llama else 'provider_snapshot_unspecified_window',
            'source_updated_at': None, 'period_end_at': None,
            'description': _text(row.get('description'), 500),
            'license_use': 'internal_research_only_pending_review',
            'actionable': False, 'demand_verified': False,
        })
    if llama:
        metric = 'fees_24h_usd' if sid.endswith('fees') else 'revenue_24h_usd'
        result.sort(key=lambda s: (s['selection_tier'] == 'primary', s['metrics'][metric] is not None, s['metrics'][metric] or 0), reverse=True)
    stats['selected_count'] = min(len(result), source['limit'])
    stats['truncated_count'] = max(0, len(result) - source['limit'])
    return result[:source['limit']]


def _load_cache(path, source):
    try:
        if path.stat().st_size > MAX_RESPONSE_BYTES:
            return None
        data = json.loads(path.read_text())
        epoch = data['fetched_epoch']
        if (data.get('schema_version') != SCHEMA_VERSION or data.get('source_url') != source['url']
                or type(epoch) not in (int, float) or not math.isfinite(epoch) or epoch > time.time()
                or not isinstance(data.get('payload'), (dict, list))):
            return None
        _normalize(source, data['payload'])
        return data
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _save_cache(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix='.live-', delete=False) as file:
            tmp = file.name
            json.dump(data, file, allow_nan=False)
        os.replace(tmp, path)
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


def _error(exc):
    if isinstance(exc, HTTPError):
        return 'http_' + str(exc.code)
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return 'timeout'
    if isinstance(exc, URLError):
        return 'network_error'
    if isinstance(exc, ValueError):
        return str(exc)[:160] if str(exc).startswith(('schema_', 'response_', 'redirect_', 'endpoint_')) else 'invalid_json'
    return type(exc).__name__


def collect_live(cache_dir, force=False):
    """Collect observations, not validated opportunities or investment recommendations.

    cache_dir must be a separate cache directory, not the existing ledger/state.
    Each source has independent freshness. Failed refreshes retain last success as stale.
    """
    now = time.time()
    output = {'schema_version': SCHEMA_VERSION, 'run_id': str(uuid4()), 'observed_at': _iso(now),
              'sources': [], 'signals': [], 'notes': [
                  'Fees are not protocol revenue; revenue is not net profit. Costs are unknown.',
                  'Boosts indicate paid promotion, not organic demand, liquidity, safety or willingness to pay.',
                  'DeFiLlama amounts are protocol-wide across reported chains, not per-chain allocations.',
                  '24h/7d windows are provider-reported; their exact period end is not supplied.',
                  'DEXScreener observations are for private internal research only pending terms review; no data resale.',
                  'Superteam listings API requires credentials. No bounty is assumed open or eligible.',
                  'Protocol selection prioritizes explicit lightweight categories; unknown categories are secondary, not inferred.',
                  'Fees and revenue are separate observations of the same entities, not independent projects.',
                  'No synthetic fallback, transactions, wallet access, accounts or paid APIs.'
              ]}
    for source in SOURCES:
        sid = source['id']
        status = {'id': sid, 'url': source['url'], 'status': 'error', 'fetched_at': None,
                  'attempted_at': None, 'error': None, 'cache_age_seconds': None,
                  'license_use': 'internal_research_only_pending_review'}
        if sid == 'superteam_listings':
            status.update(status='needs_credentials', error='Official live listings API requires Bearer key; not requested.')
            output['sources'].append(status)
            continue
        path = Path(cache_dir) / (sid + '.json')
        cached = _load_cache(path, source)
        data = cached
        if cached and not force and now - cached['fetched_epoch'] < CACHE_SECONDS:
            status['status'] = 'cached'
        else:
            status['attempted_at'] = _iso()
            try:
                payload = _fetch_json(source['url'])
                _normalize(source, payload)  # Reject changed schemas before replacing last success.
                data = {'schema_version': SCHEMA_VERSION, 'source_url': source['url'],
                        'fetched_epoch': time.time(), 'payload': payload}
                status['status'] = 'success'
                try:
                    _save_cache(path, data)
                except OSError:
                    status['cache_warning'] = 'cache_write_failed'
            except (OSError, ValueError, TypeError) as exc:
                status.update(status='stale' if cached else 'error', error=_error(exc))
        if data:
            status['fetched_at'] = _iso(data['fetched_epoch'])
            status['cache_age_seconds'] = max(0, round(time.time() - data['fetched_epoch'], 2))
            status['selection'] = {}
            for signal in _normalize(source, data['payload'], stats=status['selection']):
                signal.update(observed_at=status['fetched_at'], evidence_status={
                    'success': 'fresh', 'cached': 'cached', 'stale': 'stale'}[status['status']])
                output['signals'].append(signal)
        output['sources'].append(status)
    output['signals'] = output['signals'][:MAX_SIGNALS]
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--cache-dir', type=Path, default=Path('.live-cache'))
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    result = collect_live(args.cache_dir, force=args.force)
    # Exclusive creation prevents accidental replacement of an old ledger or report.
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as file:
        json.dump(result, file, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps({'out': str(args.out), 'signals': len(result['signals']),
                      'sources': {s['id']: s['status'] for s in result['sources']}}))


if __name__ == '__main__':
    main()
