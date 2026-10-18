"""Offline deterministic evidence ledger. No network, credentials or model API."""
import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

WEIGHTS = {
 'product': dict(pain=15, payment=20, feasibility=20, distribution=15,
                 differentiation=10, economics=10, retention=5, sharing=5),
 'bounty': dict(sponsor=25, acceptance=20, fit=20, deadline=10,
                competition=10, rights=10, follow_on=5),
}
# no_trading describes approved execution, not a ban on read-only protocol or full-stack development.
WEB3_CHECKS = ('blockchain_necessity', 'web2_difference', 'payer', 'charging_path', 'distribution')
COMMON_GATES = ['non_custodial', 'no_trading', 'no_gambling', 'no_new_spend',
                'license_clear', 'acceptance_defined', 'counterevidence_reviewed']
GATES = {'product': COMMON_GATES + ['demand_verified', 'commercial_signal_verified', 'distribution_verified'],
         'bounty': COMMON_GATES + ['open', 'eligible', 'agent_allowed', 'payment_terms_verified']}
SOURCE_STATES = {'ok', 'blocked', 'error', 'needs_credentials', 'closed', 'unverified', 'disabled'}

class Invalid(ValueError):
    pass

def require(condition, message):
    if not condition:
        raise Invalid(message)

def timestamp(value):
    require(isinstance(value, str), 'timestamp must be text')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise Invalid('invalid timestamp: ' + value) from exc
    require(result.tzinfo is not None, 'timestamp needs timezone')
    return result.astimezone(timezone.utc)

def number(value, name, minimum=0, maximum=float('inf')):
    require(type(value) in (int, float) and math.isfinite(value)
            and minimum <= value <= maximum, 'invalid number: ' + name)
    return value

def url(value):
    require(isinstance(value, str), 'URL must be text')
    require(not any(ord(c)<33 for c in value),'URL contains control characters or whitespace')
    parsed = urlsplit(value)
    require(not any(k.lower() in ('api_key','apikey','key','token','access_token','secret','password','authorization','signature','sig') for k,v in parse_qsl(parsed.query)), 'URL contains sensitive query key')
    require(parsed.scheme == 'https' and parsed.hostname and not parsed.username
            and not parsed.password, 'source URL must be credential-free HTTPS')
    return value

def canonical(value):
    p = urlsplit(url(value))
    query = urlencode(sorted((k,v) for k,v in parse_qsl(p.query)
                             if not k.lower().startswith('utm_') and k not in ('ref', 'source')))
    return urlunsplit(('https', p.netloc.lower(), p.path.rstrip('/') or '/', query, ''))

def identity(card):
    # Product-level canonical key is shared across chains; bounty key is exact listing URL.
    return card['kind'] + ':' + canonical(card['canonical_url'])

def validate(bundle, now):
    require(isinstance(bundle, dict), 'bundle must be object')
    require(bundle.get('schema_version') == 1, 'schema_version must be 1')
    require(type(bundle.get('synthetic')) is bool, 'synthetic flag required')
    generated = timestamp(bundle.get('generated_at'))
    require(generated <= now + timedelta(minutes=5), 'future bundle')
    require((now-generated).total_seconds() <= 48*3600, 'bundle older than 48 hours')
    sources = bundle.get('sources')
    evidence = bundle.get('evidence')
    cards = bundle.get('opportunities')
    require(isinstance(sources,list) and isinstance(evidence,list) and isinstance(cards,list),
            'sources, evidence, opportunities must be lists')
    require(len(cards) <= 60 and len(sources) <= 40, 'research budget exceeded')
    smap, emap = {}, {}
    for s in sources:
        require(isinstance(s,dict) and isinstance(s.get('id'),str), 'source id required')
        require(s['id'] not in smap, 'duplicate source id')
        url(s.get('url')); require(s.get('status') in SOURCE_STATES, 'invalid source state')
        require(timestamp(s.get('checked_at')) <= now + timedelta(minutes=5), 'future source')
        require(isinstance(s.get('detail'),str), 'source detail required')
        smap[s['id']] = s
    for e in evidence:
        require(isinstance(e,dict) and isinstance(e.get('id'),str), 'evidence id required')
        require(e['id'] not in emap, 'duplicate evidence id')
        require(e.get('source_id') in smap, 'unknown evidence source')
        url(e.get('url'))
        require(isinstance(e.get('excerpt'),str) and e['excerpt'].strip(), 'excerpt required')
        require(isinstance(e.get('claim'),str) and e['claim'].strip(), 'claim required')
        require(e.get('type') in ('official','user_feedback','metric','counterevidence'), 'evidence type')
        require(isinstance(e.get('metric_definition'),str), 'metric definition required (empty for non-metrics)')
        require(timestamp(e.get('observed_at')) <= now + timedelta(minutes=5), 'future evidence')
        emap[e['id']] = e
    seen = set()
    for c in cards:
        require(isinstance(c,dict) and c.get('kind') in WEIGHTS, 'invalid kind')
        require(isinstance(c.get('name'),str) and c['name'].strip(), 'name required')
        key = identity(c); require(key not in seen, 'duplicate canonical opportunity in bundle'); seen.add(key)
        for f in ('summary','target_user','pain','alternatives','mvp','distribution','monetization',
                  'counterevidence','next_step'):
            require(isinstance(c.get(f),str) and c[f].strip(), f + ' required')
        require(isinstance(c.get('chains'),list) and all(isinstance(x,str) for x in c['chains']), 'chains required')
        require(isinstance(c.get('scores'),dict) and set(c['scores']) == set(WEIGHTS[c['kind']]), 'score dimensions mismatch')
        for dim,v in c['scores'].items():
            require(isinstance(v,dict), 'score must be object')
            if v.get('value') is not None: number(v['value'],dim,0,5)
            refs = v.get('evidence_ids')
            require(isinstance(refs,list) and all(isinstance(r,str) and r in emap for r in refs),'invalid score evidence')
            require(v.get('value') is None or refs, 'known score needs evidence')
            require(isinstance(v.get('reason'),str), 'score reason required')
        require(isinstance(c.get('gates'),dict) and set(c['gates']) == set(GATES[c['kind']]), 'gates mismatch')
        for name,g in c['gates'].items():
            require(isinstance(g,dict) and (g.get('value') is None or type(g.get('value')) is bool), 'gate boolean/null required')
            refs=g.get('evidence_ids');require(isinstance(refs,list) and all(isinstance(r,str) and r in emap for r in refs),'invalid gate evidence')
            require(g.get('value') is not True or refs, 'passing gate needs evidence')
        # Additive contract: historical schema-v1 cards remain valid without a review.
        review = c.get('web3_review')
        if c['kind'] == 'product' and review is not None:
            require(isinstance(review,dict) and review.get('schema_version') == 1,
                    'web3_review schema_version must be 1')
            timestamp(review.get('reviewed_at'))
            for field in WEB3_CHECKS:
                check = review.get(field)
                require(isinstance(check,dict) and
                        (check.get('value') is None or type(check.get('value')) is bool),
                        'web3_review boolean/null required: '+field)
                require(isinstance(check.get('reason'),str) and check['reason'].strip(),
                        'web3_review reason required: '+field)
                refs = check.get('evidence_ids')
                require(isinstance(refs,list) and all(isinstance(r,str) and r in emap for r in refs),
                        'invalid web3_review evidence: '+field)
                require(check.get('value') is not True or refs,
                        'passing web3_review needs evidence: '+field)
        if c['kind'] == 'bounty':
            b=c.get('bounty'); require(isinstance(b,dict), 'bounty terms required')
            require(b.get('reward_type') in ('fixed','competition','grant','investment','in_kind'), 'reward type')
            for f in ('eligibility','agent_policy','payment_terms','rights','acceptance'):
                require(isinstance(b.get(f),str) and b[f].strip(), f+' required')
            if b.get('deadline') is not None: timestamp(b['deadline'])
            for f in ('personal_net_prize_usd','cash_cost_usd','total_hours','win_probability','payout_probability'):
                if b.get(f) is not None: number(b[f],f,0,1 if 'probability' in f else float('inf'))
            require(b.get('total_hours') != 0, 'hours must be positive or null')
            require(isinstance(b.get('scenario_only'),bool), 'scenario_only required')
    return smap,emap

def fresh(e, sources, now):
    s=sources[e['source_id']]
    return (s['status']=='ok' and
            timedelta(0) <= now-timestamp(e['observed_at']) <= timedelta(days=7) and
            timedelta(0) <= now-timestamp(s['checked_at']) <= timedelta(hours=48))

def assess_experiment(card, sources, evidence, now, synthetic=False):
    """Local-only recommendation. Internal plans never alter market evidence or claims."""
    plan=card.get('experiment_plan')
    if plan is None: return ['experiment:missing_plan']
    if not isinstance(plan,dict): return ['experiment:invalid_plan']
    reasons=[]
    def check(ok, field):
        if not ok: reasons.append('experiment:'+field)
    def text(value): return isinstance(value,str) and bool(value.strip())
    def finite(value): return type(value) in (int,float) and math.isfinite(value)
    check(card['kind']=='product','product_only')
    check(not synthetic,'synthetic_bundle')
    for field in ('target_user','workflow','falsifiable_hypothesis','stop_criteria','alternative_review'):
        check(text(plan.get(field)),field)
    try:
        age=now-timestamp(plan.get('reviewed_at'))
        check(timedelta(0)<=age<=timedelta(hours=48),'stale_plan')
    except Invalid:
        check(False,'reviewed_at')
    hours=plan.get('max_hours')
    check(finite(hours) and 0<hours<=8,'max_hours')
    cost=plan.get('incremental_cost_usd')
    check(finite(cost) and cost==0,'incremental_cost_usd')
    safety=plan.get('safety_review')
    safety=safety if isinstance(safety,dict) else {}
    check(text(safety.get('rationale')),'safety_rationale')
    for field in ('local_only','read_only','non_custodial','no_trading','no_gambling',
                  'no_payments','no_wallet_signing','no_credentials','no_external_writes',
                  'no_personal_data','no_repository_creation'):
        check(safety.get(field) is True,'safety:'+field)
    license_review=plan.get('license_review')
    license_review=license_review if isinstance(license_review,dict) else {}
    check(license_review.get('clear') is True and text(license_review.get('basis')),
          'license_review')
    acceptance=plan.get('acceptance')
    acceptance=acceptance if isinstance(acceptance,dict) else {}
    check(text(acceptance.get('metric')) and text(acceptance.get('procedure')) and
          acceptance.get('operator') in ('>=','<=','==') and finite(acceptance.get('threshold')),
          'measurable_acceptance')
    inputs=plan.get('inputs')
    check(isinstance(inputs,list) and bool(inputs),'input_provenance')
    if isinstance(inputs,list):
        for item in inputs:
            check(isinstance(item,dict) and item.get('kind') in ('synthetic','public_snapshot')
                  and text(item.get('provenance')) and text(item.get('license_basis')),
                  'input_provenance')
            if isinstance(item,dict) and item.get('kind')=='public_snapshot':
                refs=item.get('evidence_ids')
                check(isinstance(refs,list) and bool(refs) and all(
                    isinstance(x,str) and x in evidence and fresh(evidence[x],sources,now)
                    for x in refs),'input_evidence')
    for field, counter in (('problem_evidence_ids',False),('counterevidence_ids',True)):
        refs=plan.get(field)
        check(isinstance(refs,list) and bool(refs) and all(
            isinstance(x,str) and x in evidence and
            (evidence[x]['type']=='counterevidence')==counter and fresh(evidence[x],sources,now)
            for x in refs),field)
    return list(dict.fromkeys(reasons))

def assess_web3_review(card, sources, evidence, now):
    """Evidence-backed strategic gate, never a revenue claim or execution permission."""
    if card['kind'] != 'product': return []
    review = card.get('web3_review')
    if review is None: return ['missing_web3_review']
    if not isinstance(review,dict) or review.get('schema_version') != 1:
        return ['web3_review:invalid_review']
    reasons=[]
    try:
        age=now-timestamp(review.get('reviewed_at'))
        if not timedelta(0) <= age <= timedelta(hours=48):
            reasons.append('web3_review:stale_review')
    except Invalid:
        reasons.append('web3_review:invalid_reviewed_at')
    for field in WEB3_CHECKS:
        check=review.get(field)
        check=check if isinstance(check,dict) else {}
        refs=check.get('evidence_ids')
        if (check.get('value') is not True or
                not isinstance(check.get('reason'),str) or not check['reason'].strip() or
                not isinstance(refs,list) or not refs or not all(
                    isinstance(x,str) and x in evidence and fresh(evidence[x],sources,now)
                    and evidence[x]['type'] != 'counterevidence' for x in refs)):
            reasons.append('web3_review:'+field)
    return reasons

def assess(card, sources, evidence, now, synthetic=False):
    lower=coverage=0; details={}; reasons=assess_web3_review(card,sources,evidence,now)
    def supported(refs): return bool(refs) and all(fresh(evidence[x],sources,now) for x in refs)
    for name,w in WEIGHTS[card['kind']].items():
        s=card['scores'][name];v=s['value'] if supported(s['evidence_ids']) else None
        details[name]={'value':v,'weight':w,'evidence_ids':s['evidence_ids'],'reason':s['reason']}
        if v is not None: lower += w*v/5;coverage += w
    for name,g in card['gates'].items():
        if g['value'] is not True or not supported(g['evidence_ids']): reasons.append('gate:'+name)
    if not any(e['type']=='counterevidence' and fresh(e,sources,now) for e in (evidence[x] for x in card['gates']['counterevidence_reviewed']['evidence_ids'])): reasons.append('missing_fresh_counterevidence')
    cited={x for v in card['scores'].values() for x in v['evidence_ids']}
    if len({canonical(evidence[x]['url']) for x in cited if fresh(evidence[x],sources,now)}) < 2: reasons.append('needs_two_independent_sources')
    if lower < 75: reasons.append('lower_bound_below_75')
    if coverage < 75: reasons.append('coverage_below_75')
    hourly=None
    if card['kind']=='bounty':
        b=card['bounty'];deadline=b.get('deadline')
        open_refs=card['gates']['open']['evidence_ids']
        if not any(evidence[x]['type']=='official' and evidence[x].get('listing_status')=='open' and canonical(evidence[x]['url'])==canonical(card['canonical_url']) and fresh(evidence[x],sources,now) and now-timestamp(evidence[x]['observed_at'])<=timedelta(hours=24) for x in open_refs): reasons.append('missing_canonical_listing_status_evidence')
        if any(e.get('listing_status') in ('closed','revoked','expired') and canonical(e['url'])==canonical(card['canonical_url']) and fresh(e,sources,now) for e in evidence.values()): reasons.append('canonical_listing_closed')
        if deadline is None: reasons.append('unknown_deadline')
        elif timestamp(deadline) <= now: reasons.append('expired')
        elif b.get('total_hours') is None or (timestamp(deadline)-now).total_seconds()/3600 < b['total_hours']+24:
            reasons.append('insufficient_deadline_buffer')
        if b['reward_type'] in ('investment','in_kind'): reasons.append('not_cash_work_opportunity')
        fields=['win_probability','personal_net_prize_usd','payout_probability','cash_cost_usd','total_hours']
        if all(b.get(x) is not None for x in fields):
            hourly=(b['win_probability']*b['personal_net_prize_usd']*b['payout_probability']-b['cash_cost_usd'])/b['total_hours']
        if b.get('cash_cost_usd') != 0: reasons.append('cost_unknown_or_nonzero')
        if b.get('personal_net_prize_usd') is None: reasons.append('unknown_personal_award')
    if synthetic: reasons.append('synthetic_never_authorizes_development')
    experiment_blockers=assess_experiment(card,sources,evidence,now,synthetic)
    return {'key':identity(card),'name':card['name'],'kind':card['kind'],
            'lower_bound':round(lower,2),'upper_bound':round(lower+100-coverage,2),
            'coverage':coverage,'scores':details,'prototype_eligible':not reasons,
            'build_eligible':not reasons, 'experiment_eligible':not experiment_blockers,
            'experiment_blockers':experiment_blockers,
            'blockers':reasons,'expected_hourly_usd':hourly,
            'hourly_is_scenario':card.get('bounty',{}).get('scenario_only'), 'card':card}

SCHEMA='''
CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, at TEXT NOT NULL, synthetic INTEGER NOT NULL, digest TEXT UNIQUE NOT NULL, report TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sources (id TEXT PRIMARY KEY, status TEXT NOT NULL, last_check TEXT NOT NULL, last_success TEXT, detail TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS opportunities (key TEXT PRIMARY KEY, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL, assessment TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS observations (run_id TEXT, key TEXT, assessment TEXT NOT NULL, PRIMARY KEY(run_id,key));
CREATE TABLE IF NOT EXISTS development (key TEXT PRIMARY KEY, status TEXT NOT NULL, repository_url TEXT, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY, key TEXT NOT NULL, at TEXT NOT NULL, note TEXT NOT NULL);
'''

def connect(path):
    db=sqlite3.connect(path,timeout=30); db.executescript(SCHEMA);return db

def ingest(db,bundle,now):
    sources,evidence=validate(bundle,now)
    modes={row[0] for row in db.execute('SELECT DISTINCT synthetic FROM runs')}
    require(not modes or modes=={int(bundle['synthetic'])}, 'use separate databases for synthetic and real evidence')
    raw=json.dumps(bundle,sort_keys=True,ensure_ascii=False,allow_nan=False)
    digest=hashlib.sha256(raw.encode()).hexdigest()
    old=db.execute('SELECT report FROM runs WHERE digest=?',(digest,)).fetchone()
    if old:
        report=json.loads(old[0]); report['replayed']=True;report['new_build_candidates']=[];return report
    rid=now.strftime('%Y%m%dT%H%M%SZ')+'-'+digest[:10]
    results=[assess(c,sources,evidence,now,bundle['synthetic']) for c in bundle['opportunities']]
    results.sort(key=lambda r:(r['prototype_eligible'],r['lower_bound']),reverse=True)
    for r in results:
        prior=db.execute('SELECT assessment FROM opportunities WHERE key=?',(r['key'],)).fetchone()
        r['change']='new' if prior is None else ('unchanged' if json.loads(prior[0])['card']==r['card'] else 'updated')
        dev=db.execute('SELECT status,repository_url FROM development WHERE key=?',(r['key'],)).fetchone()
        r['development_status']=dev[0] if dev else None
        r['repository_url']=dev[1] if dev else None
        r['new_build_candidate']=r['prototype_eligible'] and dev is None
    report={'schema_version':1,'run_id':rid,'generated_at':now.isoformat(),'synthetic':bundle['synthetic'],
            'replayed':False,'source_health':bundle['sources'],'opportunities':results,
            'new_build_candidates':[r['key'] for r in results if r['new_build_candidate']],
            'weekly_review_due':now.weekday()==6,'evidence':bundle['evidence'], 'input_bundle':bundle,
            'cost':{'new_paid_services_usd':0,'existing_subscription_cost_usd':None},
            'notice':'Research evidence supplied by dot; no autonomous source fetching, trading, repo creation or publishing in this CLI.'}
    with db:
        for s in sources.values():
            db.execute('INSERT INTO sources VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status,last_check=excluded.last_check,last_success=COALESCE(excluded.last_success,sources.last_success),detail=excluded.detail WHERE excluded.last_check>=sources.last_check',
                       (s['id'],s['status'],timestamp(s['checked_at']).isoformat(),timestamp(s['checked_at']).isoformat() if s['status']=='ok' else None,s['detail']))
        for r in results:
            data=json.dumps(r,ensure_ascii=False,allow_nan=False)
            db.execute('INSERT INTO opportunities VALUES(?,?,?,?) ON CONFLICT(key) DO UPDATE SET last_seen=excluded.last_seen,assessment=excluded.assessment',(r['key'],now.isoformat(),now.isoformat(),data))
            db.execute('INSERT INTO observations VALUES(?,?,?)',(rid,r['key'],data))
        db.execute('INSERT INTO runs VALUES(?,?,?,?,?)',(rid,now.isoformat(),bundle['synthetic'],digest,json.dumps(report,ensure_ascii=False,allow_nan=False)))
    return report

def claim(db,key,now):
    # SQLite write lock serializes local reservations only; remote repository claims require CAS.
    db.execute('BEGIN IMMEDIATE')
    try:
        row=db.execute('SELECT assessment FROM opportunities WHERE key=?',(key,)).fetchone()
        require(row is not None,'unknown opportunity')
        item=json.loads(row[0]);require(item['prototype_eligible'],'opportunity not eligible')
        run=db.execute('SELECT r.report FROM observations o JOIN runs r ON r.id=o.run_id WHERE o.key=? ORDER BY r.at DESC LIMIT 1',(key,)).fetchone()
        require(run is not None,'missing provenance')
        bundle=json.loads(run[0])['input_bundle']
        sources,evidence=validate(bundle,now)
        for sid, status, checked, detail in db.execute('SELECT id,status,last_check,detail FROM sources'):
            if sid in sources:
                sources[sid]={**sources[sid], 'status':status,'checked_at':checked,'detail':detail}
        current=assess(item['card'],sources,evidence,now,bundle['synthetic'])
        require(current['prototype_eligible'],'current evidence no longer qualifies')
        latest=db.execute('SELECT last_seen FROM opportunities WHERE key=?',(key,)).fetchone()[0]
        require(now-timestamp(latest)<=timedelta(hours=24),'eligibility needs refresh')
        require(not db.execute('SELECT 1 FROM development WHERE key=?',(key,)).fetchone(),'already claimed; reconcile existing status')
        require(not db.execute("SELECT 1 FROM development WHERE status IN ('claimed','active','paused')").fetchone(),'WIP limit 1: resolve existing project first')
        db.execute('INSERT INTO development VALUES(?,?,?,?)',(key,'claimed',None,now.isoformat()));db.commit()
    except Exception:
        db.rollback();raise

def markdown(report):
    lines=['# Blockchain Opportunity Radar',f"Run: {report['run_id']}",f"Timestamp: {report['generated_at']}",
           '**SYNTHETIC DEMO — NOT REAL FINDINGS**' if report['synthetic'] else 'Private research report; not investment advice.',
           '', '## Source health']
    lines += [f"- {s['id']}: {s['status']} ({s['checked_at']}) — {s['detail']}" for s in report['source_health']]
    for kind in WEIGHTS:
        lines += ['',f'## {kind.title()} opportunities']
        rows=[r for r in report['opportunities'] if r['kind']==kind]
        if not rows: lines.append('No opportunities supplied.')
        for r in rows[:3]:
            lines += [f"### {r['name']}",f"Score {r['lower_bound']}–{r['upper_bound']}; coverage {r['coverage']}%; build eligible (legacy prototype_eligible): {r['prototype_eligible']}; local experiment eligible: {r.get('experiment_eligible',False)}.",
                      r['card']['summary'], f"Next: {r['card']['next_step']}", f"Counterevidence: {r['card']['counterevidence']}",
                      'Build blockers: '+(', '.join(r['blockers']) or 'none'),
                      'Local experiment blockers: '+(', '.join(r.get('experiment_blockers',['experiment:missing_plan'])) or 'none'),f"Source: {r['card']['canonical_url']}"]
            for d,s in r['scores'].items(): lines.append(f"- {d}: {s['value']} / 5; evidence {', '.join(s['evidence_ids'])}; {s['reason']}")
    lines += ['', '## Safeguards',report['notice'],'Unknown values remain null. No candidate is required to pass. Full cards and history are in JSON/SQLite.']
    return '\n'.join(lines)+'\n'
