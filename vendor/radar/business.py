"""Evidence-aware research cards. Pure functions; no network or action executor.

Rule mappings are product hypotheses, not evidence or investment recommendations.
Only the existing validated ledger can establish build eligibility.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import ipaddress
from urllib.parse import urlsplit
from . import core

MAX_IMPORT_BYTES = 64 * 1024
ARCHETYPES = {
    'payfi': {
        'keywords': ('payfi', 'payment', 'x402', 'commerce', 'invoice'),
        'job': 'Reconcile public settlement receipts and API usage without moving funds.',
        'necessity': 'Public settlement verification may help cross-organization reconciliation; compare with a conventional receipt database.',
        'motivation': ['autonomy', 'convenience'],
        'model': 'Transparent usage-based reconciliation or reporting fee; payment integration is a separate reviewed milestone.',
        'channel': 'Developer documentation and a read-only merchant reconciliation demo.',
        'difference': 'Explain mismatched receipts and expose source timestamps, rather than adding another payment button.',
        'test': 'Replay ten labelled receipt/usage pairs locally and identify every intentional mismatch without signing or paying.',
        'docs': ['https://docs.cdp.coinbase.com/x402/welcome', 'https://solana.com/docs/rpc'],
    },
    'wallet_utility': {
        'keywords': ('wallet', 'dust', 'yield', 'portfolio', 'aggregator'),
        'job': 'Understand token holdings, liquidity and estimated service costs before making any decision.',
        'necessity': 'Public on-chain balances and token metadata are intrinsic inputs; no wallet connection is needed for a local sample.',
        'motivation': ['autonomy', 'convenience'],
        'model': 'Clearly disclosed analysis/report subscription; hypothetical routing fees are not implemented or earned.',
        'channel': 'Wallet-support workflows and opt-in educational reports.',
        'difference': 'Show uncertainty, unsupported tokens and total fee estimates instead of anxiety-driven clean-up prompts.',
        'test': 'Use a public/synthetic wallet snapshot to explain ten holdings, including unknown liquidity, with zero transactions.',
        'docs': ['https://solana.com/docs/rpc', 'https://developers.jup.ag/docs/swap'],
    },
    'social_tools': {
        'keywords': ('social', 'community', 'creator', 'farcaster', 'reputation'),
        'job': 'Help communities explain public participation and let members export an optional factual profile.',
        'necessity': 'Portable on-chain attestations might add value; an ordinary community database may be sufficient.',
        'motivation': ['community', 'status', 'autonomy'],
        'model': 'Transparent community analytics subscription, not speculative token issuance or paid ranking.',
        'channel': 'Community operator interviews and opt-in shareable reports; no automatic posting.',
        'difference': 'Source-linked, correctable participation summaries rather than fabricated rankings or shaming.',
        'test': 'Render three source-linked participation summaries and verify correction/export controls on a local sample.',
        'docs': ['https://docs.neynar.com/', 'https://solana.com/docs'],
    },
    'transparency': {
        'keywords': ('transparency', 'boost', 'launchpad', 'terminal', 'trading', 'prediction', 'gambl', 'fees', 'revenue'),
        'job': 'Distinguish paid promotion, protocol fees, protocol revenue and unsupported profit claims.',
        'necessity': 'Public protocol economics can be checked against on-chain sources; blockchain is not needed for every UI component.',
        'motivation': ['autonomy', 'convenience', 'community'],
        'model': 'Transparent research/API subscription if users validate the need; no trading, betting or guaranteed returns.',
        'channel': 'Source-linked analyst reports and developer integrations, not paid-boost chasing.',
        'difference': 'Put definitions, missing cost data and counterevidence next to every metric.',
        'test': 'Classify ten metric records as fees, revenue or promotion and preserve unknown profit in every export.',
        'docs': ['https://api-docs.defillama.com/llms-free.txt', 'https://docs.dexscreener.com/api/reference'],
    },
    'data_agent': {
        'keywords': ('agent', 'data', 'analytics', 'mcp', 'intelligence'),
        'job': 'Turn public protocol data into reproducible, source-linked answers for a specific operator workflow.',
        'necessity': 'On-chain data is useful only when it answers a task unavailable from a simpler conventional source.',
        'motivation': ['autonomy', 'convenience'],
        'model': 'Transparent metered data/reporting fee or subscription, subject to willingness-to-pay evidence.',
        'channel': 'Developer workflows, reproducible examples and an opt-in design-partner test.',
        'difference': 'Auditable calculations, failure states and source provenance instead of opaque alpha promises.',
        'test': 'Answer ten labelled workflow questions from local snapshots with citations and explicit unknowns.',
        'docs': ['https://solana.com/docs/rpc', 'https://api-docs.defillama.com/llms-free.txt'],
    },
}


# These are target-product slices, not the scanner's own architecture.
PRODUCT_PLANS = {
    'payfi': {
        'wedge': 'Receipt Gap Desk: explain mismatches between an API operator’s usage records and public settlement receipts.',
        'journey': 'Operator opens a local fixture batch → compares usage and receipt rows → inspects unmatched/duplicate entries → exports an exceptions report. No payment collection.',
        'routes': ['/reconcile/batches', '/reconcile/batches/:batchId', '/reconcile/exceptions/:exceptionId'],
        'endpoints': ['POST /api/reconciliation/batches (local fixture upload only)', 'GET /api/reconciliation/batches/{id}/exceptions', 'GET /api/reconciliation/batches/{id}/report'],
        'models': ['UsageRecord(id, request_id, amount_minor, asset, occurred_at)', 'SettlementReceipt(id, signature, asset, amount_minor, source_url, observed_at)', 'ReceiptMatch(usage_id, receipt_id, status, reason)'],
        'jobs': ['match_receipts(batch_id): idempotent request-id and exact decimal matching; ambiguous matches stay unresolved'],
        'interfaces': ['Solana RPC getTransaction/getSignatureStatuses via recorded response adapter; distinguish observed confirmation from merchant-paid status.', 'x402 verification/settlement interface is disabled and unconfigured; no forged payment proof, facilitator requests or collection.'],
        'fixture': '10 usage records: 6 unique exact receipts, 1 duplicate receipt, 1 wrong asset, 1 wrong amount, 1 missing receipt.',
        'acceptance': 'Exactly 6 matched and 4 exceptions; duplicate never counted twice; all 10 preserve source/fixture provenance; report has zero paid/settled claims beyond the fixture labels.',
        'stop': 'Stop if matching needs private billing data, a payment key, live settlement or more than one network; record ambiguity rather than auto-resolve.',
    },
    'wallet_utility': {
        'wedge': 'Token Inventory Explainer: explain why a small public wallet holding is unpriced or unsupported, without proposing a trade.',
        'journey': 'User opens a sample inventory → sorts unresolved holdings → expands token metadata/liquidity explanations → exports a read-only inventory. No connect-wallet or sweep button.',
        'routes': ['/inventory/samples', '/inventory/:sampleId', '/inventory/:sampleId/token/:mint'],
        'endpoints': ['GET /api/inventories/{sampleId}', 'GET /api/inventories/{sampleId}/tokens/{mint}/explanation', 'GET /api/inventories/{sampleId}/export'],
        'models': ['InventorySnapshot(id, chain, block_slot, observed_at, provenance)', 'TokenHolding(snapshot_id, mint, raw_amount, decimals, price_usd_nullable)', 'LiquidityObservation(mint, pair_url, observed_at, status, explanation)'],
        'jobs': ['normalize_inventory(snapshot_id): exact integer token quantities; join metadata without inferring price from balance'],
        'interfaces': ['Recorded Solana RPC getTokenAccountsByOwner/getAccountInfo responses with SPL/Token-2022 labels.', 'Optional recorded DEX pair data for internal analysis only; Jupiter trade-building and EIP-5792 wallet calls disabled.'],
        'fixture': '10 holdings: 6 priced, 2 price unknown, 1 metadata missing, 1 unsupported token extension; include 6- and 9-decimal quantities.',
        'acceptance': 'All 10 amounts round-trip exactly; 4 unresolved holdings display explicit reasons; unknown prices never become zero or 100% loss; no transaction/signing request exists.',
        'stop': 'Stop if a token requires executable metadata, user credentials, live wallet access or trade construction; leave it unsupported.',
    },
    'social_tools': {
        'wedge': 'Community Attribution Notebook: let a small community inspect source attribution and reuse-permission gaps before preparing a factual contribution profile.',
        'journey': 'Moderator opens a sample contribution set → checks attribution and available license evidence → member previews/corrects a local profile → exports an optional private preview. No public posting or inferred ownership.',
        'routes': ['/community/contributions', '/community/contributions/:id/attribution', '/community/profiles/:memberId/preview'],
        'endpoints': ['GET /api/community/contributions', 'POST /api/community/corrections (local-only review draft)', 'GET /api/community/profiles/{id}/preview'],
        'models': ['Contribution(id, author_label, source_url, content_hash, observed_at)', 'AttributionEvidence(contribution_id, license_label_nullable, evidence_url, status)', 'ProfileCorrection(id, contribution_id, proposed_text, review_status)'],
        'jobs': ['assemble_profile(member_id): include only selected source-linked facts; deduplicate content hashes; mark disputed attribution'],
        'interfaces': ['Recorded public community/API responses and optional Solana attestation account reads; chain presence does not prove copyright or reuse permission.', 'No token minting, wallet identity linking, social-account OAuth, publishing or platform writes.'],
        'fixture': '8 contributions: 4 with explicit source/license labels, 2 unknown reuse permissions, 1 duplicate, 1 disputed attribution; one local correction draft.',
        'acceptance': 'Preview contains 7 deduplicated entries; 2 permission gaps and 1 dispute remain visible; correction never changes original evidence; export is optional and no ranking/ownership claim is fabricated.',
        'stop': 'Stop before collecting personal identifiers, claiming legal ownership, publishing a profile or reusing an asset without established permission.',
    },
    'transparency': {
        'wedge': 'Fee Definition Comparator: help one protocol analyst reconcile fee versus revenue disclosures and identify paid-promotion evidence.',
        'journey': 'Analyst chooses two recorded protocol observations → aligns periods and definitions → opens a discrepancy explanation → exports a source-linked comparison, not an investment ranking.',
        'routes': ['/economics/compare', '/economics/protocol/:slug/definitions', '/economics/comparisons/:id'],
        'endpoints': ['POST /api/economics/comparisons (local observation IDs)', 'GET /api/economics/comparisons/{id}', 'GET /api/economics/definitions'],
        'models': ['EconomicObservation(id, protocol_slug, metric_kind, period_start, period_end, amount_nullable, source_url)', 'MetricDefinition(id, metric_kind, supply_side_treatment, incentives_treatment)', 'ComparisonIssue(comparison_id, observation_id, issue_code, explanation)'],
        'jobs': ['compare_definitions(comparison_id): reject unlike periods; never merge protocol fees with paid-boost counts'],
        'interfaces': ['Recorded DeFiLlama dailyFees/dailyRevenue overview responses; recorded DEX boosts explicitly labelled paid promotion.', 'No trading route or execution adapter. External data resale stays disabled pending licensing review.'],
        'fixture': '10 observations: 4 fees, 3 revenue, 2 paid boosts, 1 unknown kind; include one mismatched period and no operating-cost evidence.',
        'acceptance': 'All 10 retain original metric types; unknown kind and mismatched period are flagged; all net-profit fields remain null; paid boosts never contribute to organic-demand or safety scores.',
        'stop': 'Stop if source definitions are missing or periods cannot be aligned; return incomparable rather than manufacturing a ratio or net profit.',
    },
    'data_agent': {
        'wedge': 'Protocol Answer Trace: give a developer reproducible answers to a narrow set of protocol-data questions with inspectable calculation steps.',
        'journey': 'Developer selects a supported question → runs it on a local source snapshot → inspects answer, calculation and citations → exports a reproducible response fixture. Unsupported questions abstain.',
        'routes': ['/answers/questions', '/answers/runs/:runId', '/answers/runs/:runId/trace'],
        'endpoints': ['POST /api/answers/runs (allowlisted question + snapshot IDs)', 'GET /api/answers/runs/{id}', 'GET /api/answers/runs/{id}/trace'],
        'models': ['SourceSnapshot(id, source_url, retrieved_at, content_hash, license_status)', 'QuestionTemplate(id, required_fields, deterministic_operation)', 'AnswerRun(id, template_id, snapshot_ids, result_nullable, abstention_reason, trace)'],
        'jobs': ['compute_answer(run_id): deterministic allowlisted operations; enforce source age and units; no arbitrary code or autonomous tools'],
        'interfaces': ['Recorded Solana RPC or DeFiLlama response adapter selected by question template, not arbitrary user-supplied URLs.', 'MCP-style query schema may be documented; no agent credentials, payment gateway, arbitrary fetch, signing or execution.'],
        'fixture': '10 questions: 6 answerable with supplied snapshots, 2 missing a required field, 1 stale-source question, 1 unsupported operation.',
        'acceptance': '6 exact expected answers with trace/citations and 4 explicit abstentions; repeated snapshot/template input yields identical results; no invented data, pricing or paid-status flag.',
        'stop': 'Stop when a question needs unavailable data, an external model/API subscription, arbitrary tool execution or uncited inference; return abstention.',
    },
}


def _public_source_url(value):
    core.url(value)
    host = urlsplit(value).hostname.lower().rstrip('.')
    core.require('.' in host and not any(host == suffix or host.endswith('.' + suffix)
                 for suffix in ('localhost', 'local', 'internal', 'test', 'invalid')),
                 'source must use a public hostname')
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return value
    core.require(address.is_global, 'private or reserved source IP forbidden')
    return value


def _sources(signal):
    refs = signal.get('source_refs', [])
    if not isinstance(refs, list):
        refs = []
    refs = [r.get('url') if isinstance(r, dict) else r for r in refs]
    refs += [signal.get(k) for k in ('source_url', 'canonical_url', 'url') if signal.get(k)]
    result = []
    for ref in refs:
        try:
            _public_source_url(ref)
        except (ValueError, TypeError):
            continue
        if ref not in result:
            result.append(ref)
    return result


def analyze_signal(signal):
    """Create a conservative product card from a collector signal.

    Optional evidence_bundle is revalidated against wall-clock UTC and assessed by
    core. A score, gate or eligibility flag supplied directly in a signal is ignored.
    """
    core.require(isinstance(signal, dict), 'signal must be an object')
    text = ' '.join(str(signal.get(k, '')) for k in
                    ('category', 'kind', 'type', 'name', 'title', 'description', 'source')).lower()
    key = next((k for k, rule in ARCHETYPES.items()
                if any(word in text for word in rule['keywords'])), 'data_agent')
    rule = ARCHETYPES[key]
    title = str(signal.get('title') or signal.get('name') or 'Unverified research lead')[:240]
    refs = _sources(signal)
    missing = ['customer_problem', 'willingness_to_pay', 'distribution_access',
               'differentiation_test', 'operating_costs', 'retention', 'fresh_counterevidence']
    dimensions = {name: None for name in core.WEIGHTS['product']}
    gates = {name: None for name in core.GATES['product']}
    gates.update({'web3_review:' + name: None for name in core.WEB3_CHECKS})
    missing.extend('web3_review:' + name for name in core.WEB3_CHECKS)
    lower, upper, coverage, eligible = 0, 100, 0, False
    blockers = ['No validated product evidence bundle; market evidence is unknown.']
    bundle = signal.get('evidence_bundle')
    if (bundle is not None and signal.get('provenance') != 'external_unverified'
            and not signal.get('synthetic') and not signal.get('demo')):
        try:
            now = datetime.now(timezone.utc)
            sources, evidence = core.validate(bundle, now)
            candidates = [c for c in bundle['opportunities'] if c['kind'] == 'product'
                          and c.get('canonical_url') == signal.get('canonical_url')]
            core.require(len(candidates) == 1, 'exactly one matching product is required')
            result = core.assess(candidates[0], sources, evidence, now, bundle['synthetic'])
            lower, upper, coverage = result['lower_bound'], result['upper_bound'], result['coverage']
            dimensions = {name: item['value'] for name, item in result['scores'].items()}
            gates = {name: (gate['value'] if gate['evidence_ids'] and all(
                core.fresh(evidence[r], sources, now) for r in gate['evidence_ids']) else None)
                for name, gate in candidates[0]['gates'].items()}
            review = candidates[0].get('web3_review') or {}
            review_blockers = core.assess_web3_review(candidates[0], sources, evidence, now)
            for name in core.WEB3_CHECKS:
                field = 'web3_review:' + name
                passed = (not any(reason in review_blockers for reason in
                          ('missing_web3_review', 'web3_review:invalid_review',
                           'web3_review:stale_review', 'web3_review:invalid_reviewed_at', field)))
                gates[field] = True if passed else (False if review.get(name, {}).get('value') is False else None)
            eligible = result['build_eligible']
            blockers = result['blockers']
            missing = [name for name, value in dimensions.items() if value is None]
            missing.extend('web3_review:' + name for name in core.WEB3_CHECKS
                           if gates['web3_review:' + name] is not True)
            refs = list(dict.fromkeys(refs + [e['url'] for e in evidence.values()]))
        except (ValueError, KeyError, TypeError) as exc:
            blockers = ['Evidence bundle rejected: ' + str(exc)]
    return {
        'id': str(signal.get('id') or hashlib.sha256((title + '|'.join(refs)).encode()).hexdigest()[:16]),
        'title': title, 'archetype': key,
        'web3_necessity': {'hypothesis': rule['necessity'], 'verified': None},
        'customer_job': {'hypothesis': rule['job'], 'validated': None},
        'psychology': {'motivations': rule['motivation'], 'design': 'User control, clear provenance, optional sharing and transparent fees.',
                       'prohibited': ['fake urgency', 'guaranteed returns', 'gambling compulsion', 'hidden fees']},
        'monetization': {'hypothesis': rule['model'], 'paid_demand': None, 'net_profit': None,
                         'metrics': deepcopy(signal.get('metrics', {})),
                         'warning': 'Protocol fees are not protocol revenue or operator net profit. Paid boosts are advertising, not organic demand.'},
        'distribution': {'hypothesis': rule['channel'], 'verified': None},
        'differentiation': {'hypothesis': rule['difference'], 'verified': None},
        'counterevidence': ['Observed incumbents may already solve this problem.',
                            'Promotion and fee activity do not establish demand for this proposed product.',
                            'No new customer conversion, operating-cost or retention evidence is implied.'],
        'score_lower': lower, 'score_upper': upper, 'coverage': coverage,
        'market_scores': dimensions, 'hard_gates': gates, 'build_eligible': eligible,
        'build_blockers': blockers, 'missing_evidence': missing,
        'next_test': PRODUCT_PLANS[key]['fixture'] + ' ' + PRODUCT_PLANS[key]['acceptance'],
        'source_refs': refs, 'observed_at': signal.get('observed_at'),
        'evidence_status': signal.get('evidence_status', 'unverified'),
        'license_use': signal.get('license_use', 'requires_review'),
        'provenance': signal.get('provenance', 'collector_observation'),
        'official_api_docs': [{'url': u, 'status': 'reference_only_verify_current_contract_before_integration'} for u in rule['docs']],
    }


def scenario(volume=None, fee_bps=None, share=None, costs=None, *, conversion=None,
             period='day', currency='USD'):
    """Hypothetical captured volume × fee rate × retained revenue share.

    volume is addressable transaction volume, NOT fees/revenue/boost count. share is
    the retained fraction after partner splits; conversion is captured volume share.
    Both fractions must be explicit. costs is total operating cost for the period,
    a fully enumerated dict of costs, or None (unknown). No forecast is implied.
    """
    for name, value in [('period', period), ('currency', currency)]:
        core.require(isinstance(value, str) and 0 < len(value) <= 32
                     and all(ord(c) >= 32 for c in value), 'invalid scenario ' + name)
    for name, value, maximum in [('volume', volume, float('inf')),
                                 ('fee_bps', fee_bps, 10000), ('share', share, 1),
                                 ('conversion', conversion, 1)]:
        if value is not None:
            core.number(value, name, 0, maximum)
    if isinstance(costs, dict):
        core.require(bool(costs), 'empty costs do not establish zero costs')
        for name, value in costs.items():
            if value is not None:
                core.number(value, 'cost:' + str(name))
        total_cost = sum(costs.values()) if all(v is not None for v in costs.values()) else None
    else:
        if costs is not None:
            core.number(costs, 'costs')
        total_cost = costs
    captured = volume * conversion if volume is not None and conversion is not None else None
    gross = captured * (fee_bps / 10000) if captured is not None and fee_bps is not None else None
    retained = gross * share if gross is not None and share is not None else None
    net = retained - total_cost if retained is not None and total_cost is not None else None
    core.require(all(value is None or math.isfinite(value)
                     for value in (captured, gross, retained, total_cost, net)), 'scenario arithmetic overflow')
    return {'scenario_only': True, 'currency': currency, 'period': period,
            'assumptions': {'volume': volume, 'fee_bps': fee_bps, 'share': share,
                            'conversion': conversion, 'costs': deepcopy(costs)},
            'captured_volume': captured, 'gross_fees': gross, 'retained_revenue': retained,
            'total_costs': total_cost, 'net_profit': net,
            'warning': 'Illustrative arithmetic, not expected income. Unknown costs keep net profit null.'}


MUSE_FIELDS = {'id', 'title', 'name', 'category', 'description', 'source_refs', 'source_url',
               'observed_at', 'claims', 'counterevidence', 'metrics'}
MUSE_METRICS = {'fees_24h_usd', 'revenue_24h_usd', 'fees_7d_usd', 'revenue_7d_usd',
                'volume_24h_usd', 'boost_amount', 'boost_total_amount'}


def validate_muse_import(payload):
    """Validate an inert external research lead, never an instruction or authority."""
    if isinstance(payload, bytes):
        core.require(len(payload) <= MAX_IMPORT_BYTES, 'Muse import exceeds 64 KiB')
        try:
            payload = payload.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise core.Invalid('Muse import must be UTF-8') from exc
    if isinstance(payload, str):
        core.require(len(payload.encode('utf-8')) <= MAX_IMPORT_BYTES, 'Muse import exceeds 64 KiB')
        try:
            payload = json.loads(payload)
        except (ValueError, RecursionError) as exc:
            raise core.Invalid('Muse import must be valid JSON') from exc
    core.require(isinstance(payload, dict), 'Muse import must be one object')
    core.require(set(payload) <= MUSE_FIELDS, 'Muse import has forbidden fields')
    try:
        raw = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError, RecursionError) as exc:
        raise core.Invalid('Muse import must contain finite JSON data') from exc
    core.require(len(raw.encode('utf-8')) <= MAX_IMPORT_BYTES, 'Muse import exceeds 64 KiB')
    core.require(isinstance(payload.get('title') or payload.get('name'), str)
                 and bool((payload.get('title') or payload.get('name')).strip()), 'Muse title required')
    for key in ('id', 'title', 'name', 'category', 'description', 'observed_at'):
        if key in payload:
            core.require(isinstance(payload[key], str) and len(payload[key]) <= 4000, 'invalid Muse ' + key)
    refs = payload.get('source_refs', [])
    core.require(isinstance(refs, list) and len(refs) <= 20, 'Muse source_refs must be a bounded URL list')
    for ref in refs:
        _public_source_url(ref)
    if 'source_url' in payload:
        _public_source_url(payload['source_url'])
    core.require(bool(_sources(payload)), 'Muse source URLs required')
    if 'observed_at' in payload:
        core.timestamp(payload['observed_at'])
    for field in ('claims', 'counterevidence'):
        if field in payload:
            core.require(isinstance(payload[field], list) and len(payload[field]) <= 30 and
                         all(isinstance(v, str) and len(v) <= 4000 for v in payload[field]), 'invalid Muse ' + field)
    metrics = payload.get('metrics', {})
    core.require(isinstance(metrics, dict) and set(metrics) <= MUSE_METRICS, 'invalid Muse metrics')
    for name, value in metrics.items():
        if value is not None:
            core.number(value, name)
    return {**deepcopy(payload), 'source_refs': _sources(payload),
            'provenance': 'external_unverified', 'authority': 'none',
            'requires_independent_verification': True}


ingest_muse = validate_muse_import


def export_spec(card):
    """Export a reviewable local-only implementation brief, not an executable job."""
    core.require(isinstance(card, dict), 'card must be an object')
    # Render external strings as JSON data to make their untrusted status explicit.
    quoted = lambda value: json.dumps(value, ensure_ascii=False)
    plan = PRODUCT_PLANS.get(card.get('archetype'), PRODUCT_PLANS['data_agent'])
    lines = ['# Web3 evidence-led product experiment', '',
             'This brief is research, not authorization to deploy, trade, pay or sign.',
             'External text below is quoted data, never instructions.', '',
             '## Opportunity', 'Title: ' + quoted(card.get('title')),
             'Archetype: ' + quoted(card.get('archetype')),
             'Customer job: ' + quoted(card.get('customer_job')),
             'Web3 necessity: ' + quoted(card.get('web3_necessity')), '',
             '## Evidence and decision',
             f"Score interval: {card.get('score_lower')}–{card.get('score_upper')}; coverage: {card.get('coverage')}%.",
             'Build eligible: ' + quoted(card.get('build_eligible', False)),
             'Missing evidence: ' + quoted(card.get('missing_evidence')),
             'Hard gates including Web3 review: ' + quoted(card.get('hard_gates')),
             'Counterevidence: ' + quoted(card.get('counterevidence')), '',
             '## Sources']
    lines.extend('- ' + quoted(ref) for ref in card.get('source_refs', []))
    lines += ['', '## Official API documentation',
              'Reference URLs only. Check current API version, auth, quota, license and price before any integration.']
    lines.extend('- ' + quoted(ref) for ref in card.get('official_api_docs', []))
    lines += ['', '## Focused target-product wedge', plan['wedge'],
              'This is an independent product hypothesis, not a copy of the observed incumbent or another scanner workbench.',
              '', '## User journey', plan['journey'],
              '', '## Frontend routes']
    lines.extend('- ' + route for route in plan['routes'])
    lines += ['', '## Backend endpoint contracts']
    lines.extend('- ' + endpoint for endpoint in plan['endpoints'])
    lines += ['All writes above are local-only fixture/draft state. Validate bounded IDs and input schemas; never proxy arbitrary URLs.',
              '', '## SQLite data models']
    lines.extend('- ' + model for model in plan['models'])
    lines += ['', '## Worker jobs']
    lines.extend('- ' + job for job in plan['jobs'])
    lines += ['', '## Protocol read interfaces and disabled execution boundary']
    lines.extend('- ' + interface for interface in plan['interfaces'])
    lines += ['- Keep protocol adapters versioned; any execution/payment adapter is disabled and unconfigured.',
              '- Jupiter Swap V2 has distinct order/execute and build contracts; x402 needs real verification and settlement.',
              '- EIP-5792 atomic capability must be probed before any later separately authorized integration.',
              '', '## First implementation slice and exact acceptance',
              '0–1h: define typed models and the fixture below; 1–3h: implement one endpoint plus deterministic worker;',
              '3–6h: implement the primary journey and exception view; 6–8h: run the fixture assertions and export the result.',
              'Fixture: ' + plan['fixture'], 'Acceptance: ' + plan['acceptance'],
              'Product-specific stop: ' + plan['stop'],
              '', '## Monetization and ethical design', quoted(card.get('monetization')),
              quoted(card.get('psychology')), '', '## Acceptance and next milestone (maximum 8 hours)',
              'Incremental budget: $0. Use existing local tooling and licensed public/synthetic fixtures.',
              'Next test: ' + quoted(card.get('next_test')),
              '- Acceptance: source provenance and null unknowns survive API/UI/export round-trip.',
              '- Acceptance: fee, revenue and paid-promotion labels remain distinct; unknown costs produce null net profit.',
              '- Acceptance: missing market evidence cannot pass the unchanged score >=75 and coverage >=75 gates.',
              '- Stop after 8 hours or if a dependency requires new credentials, new costs, unavailable rights or external writes.',
              '- Record test failures and demand gaps; a successful demo does not validate customer demand.',
              '', '## Non-goals and authorization boundary',
              'No real trading, payments, wallet actions, private keys, custody, token issuance, gambling, public release,',
              'external submission, outreach or automatic project/repository creation. No copied branding, assets or proprietary code.',
              'Use independent visual identity and review licenses, including restrictions on republishing or reselling source data.',
              'Standard protocols are not risk-free. Guide claims of 75–85% success or guaranteed six-hour profit are unsupported.',
              'Any later funded integration or launch is a separate decision, not granted by this brief.', '']
    return '\n'.join(lines)


export_markdown = export_spec
