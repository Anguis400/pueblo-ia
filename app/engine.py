"""Pueblo IA: scouts for verifiable public opportunities, no automated purchases or outreach.
All data from remote pages is UNTRUSTED and cannot instruct this application.
"""
import datetime as dt
import html
import json
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

UTC = dt.timezone.utc
SOURCE_TIMEOUT = 18
SCOUTS = {"remote": "Observatorio de trabajo remoto", "freelance": "Radar de encargos públicos"}
SIGNALS = {
    "automatización": 5, "automation": 5, "automate": 4,
    "python": 4, "excel": 4, "spreadsheet": 4, "google sheets": 4,
    "power bi": 4, "dashboard": 3, "data analyst": 3,
    "etl": 3, "api integration": 3, "api integrations": 3,
    "web scraping": 1, "wordpress": 2, "no-code": 2,
    "low-code": 2, "workflow": 2, "freelance": 2, "contractor": 2,
}

class _StripHTML(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []
    def handle_data(self, data): self.parts.append(data)

def public_text(text):
    """Suppress contact details and common credential patterns before publication."""
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[contacto omitido]", str(text))
    text = re.sub(r"(?:\+?\d[\d ()-]{7,}\d)", "[número omitido]", text)
    return re.sub(r"(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{12,}|Bearer\s+\S+)", "[credencial omitida]", text, flags=re.I)

def plain(raw):
    stripper = _StripHTML()
    try: stripper.feed(str(raw or "")[:12000])
    except Exception: return ""
    return public_text(re.sub(r"\s+", " ", html.unescape(" ".join(stripper.parts))).strip())

def fetch_json(url):
    request = urllib.request.Request(url, headers={
        "User-Agent": "PuebloIA-Research/1.0 (+noncommercial prototype; public APIs only)",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(request, timeout=SOURCE_TIMEOUT) as response:
        if response.status != 200: raise ValueError(f"HTTP {response.status}")
        data = response.read(1800000)
    return json.loads(data)

def safe_url(url, permitted_hosts):
    try:
        u = urllib.parse.urlparse(str(url))
        return str(url) if (u.scheme == 'https' and u.hostname in permitted_hosts
                            and not u.username and not u.password and len(str(url)) < 1200
                            and not re.search(r'(token|secret|key|email|auth)=', u.query, re.I)) else None
    except Exception: return None

def score(text):
    text = plain(text).lower()
    points = sum(weight for word, weight in SIGNALS.items() if word in text)
    # This is a deterministic ranking heuristic, NOT a prediction of earnings.
    return min(30, points)

def get_jobicy(geo="europe", fetch=fetch_json):
    url = "https://jobicy.com/api/jobs?" + urllib.parse.urlencode({"count": 100, "geo": geo})
    data = fetch(url)
    if not isinstance(data, dict) or not isinstance(data.get('jobs'), list):
        raise ValueError("Jobicy did not return a valid jobs list")
    items = []
    for job in data['jobs']:
        if not isinstance(job, dict): continue
        link = safe_url(job.get('url', ''), {'jobicy.com', 'www.jobicy.com'})
        if not link: continue
        title = plain(job.get('jobTitle') or job.get('title'))[:150]
        description = plain(job.get('jobDescription') or job.get('description'))[:350]
        company = plain(job.get('companyName') or job.get('company'))[:110]
        region = plain(job.get('jobGeo') or job.get('location'))[:100]
        suitability = score(title + " " + description)
        if suitability < 3: continue
        items.append({
            'id': 'jobicy-' + str(job.get('id') or link.rsplit('/', 1)[-1]),
            'agent': 'research', 'source': 'Jobicy', 'category': 'empleo_remoto',
            'title': title, 'company': company, 'region': region or geo,
            'url': link, 'published': str(job.get('pubDate') or '')[:45],
            'excerpt': description, 'score': suitability,
            'status': 'Oportunidad detectada; elegibilidad y vigencia por verificar',
            'revenue_eur': None, 'expense_eur': None,
        })
    return items

# A keyword such as "freelance" does NOT prove that someone wants to buy work.
# The radar intentionally favors precision over recall; missing a lead is safer
# than presenting self-promotion as demand from a potential paying customer.
SELLER_PROFILE = re.compile(
    r"(?:\bseeking work\b|\bavailable for hire\b|\bopen to work\b|"
    r"\blooking for (?:work|a job|jobs|projects|new opportunities|freelance work|freelance projects|contract work)\b|"
    r"\bwilling to relocate\s*:|\bresume\s*/\s*cv\s*:|"
    r"\blocation\s*:.*\btechnologies\s*:)", re.I)
BUYER_SIGNALS = (
    re.compile(r"\b(?:we|our (?:team|company|startup)|i)\s+(?:are\s+|am\s+|currently\s+|would\s+like\s+to\s+)?(?:looking\s+to\s+hire|hiring|looking\s+for|need|require|seeking)\b", re.I),
    re.compile(r"\b(?:looking\s+for|seeking|need(?:ing)?|hiring|wanted|required)\s+(?:(?:an?|some)\s+)?(?:freelancer|contractor|developer|engineer|designer|consultant|data analyst|automation expert|python expert)\b", re.I),
    re.compile(r"\b(?:need\s+help\s+with|looking\s+for\s+help\s+with|can\s+someone\s+(?:build|create|develop|help)|paying\s+someone\s+to)\b", re.I),
)

def buyer_intent(raw):
    """Conservative triage only; not proof of client, budget or deal."""
    body = plain(raw)[:6000]
    if SELLER_PROFILE.search(body):
        return False
    return any(pattern.search(body) for pattern in BUYER_SIGNALS)

def get_hn(query='freelance', fetch=fetch_json):
    base = "https://hn.algolia.com/api/v1/search_by_date?"
    data = fetch(base + urllib.parse.urlencode({"query": query, "tags":"comment", "hitsPerPage": 100}))
    if not isinstance(data, dict) or not isinstance(data.get('hits'), list):
        raise ValueError("HN Algolia response invalid")
    items = []
    earliest = dt.datetime.now(UTC) - dt.timedelta(days=21)
    for hit in data['hits']:
        if not isinstance(hit, dict): continue
        raw_date = str(hit.get('created_at') or '')
        try:
            published = dt.datetime.fromisoformat(raw_date.replace('Z','+00:00'))
            if published < earliest: continue
        except (ValueError, TypeError): continue
        body = plain(hit.get('comment_text') or '')
        # Exclude profiles from people selling services. Demand must be explicit.
        if not buyer_intent(body):
            continue
        suitability = score(body)
        if suitability < 5: continue
        object_id = str(hit.get('objectID') or '')
        if not object_id.isdigit(): continue
        items.append({
            'id': 'hn-' + object_id, 'agent': 'sales', 'source': 'Hacker News / Algolia',
            'category': 'posible_encargo_no_verificado',
            'title': 'Petición pública sin verificar: ' + plain(body[:85]),
            'company': '', 'region': 'No comprobada',
            'url': 'https://news.ycombinator.com/item?id=' + object_id,
            'published': raw_date, 'excerpt': body[:320], 'score': suitability,
            'status': 'Posible comprador: verificar necesidad, presupuesto y vigencia antes de contactar',
            'revenue_eur': None, 'expense_eur': None,
        })
    return items

def unique_ranked(items, limit=24):
    dedup = {}
    for row in items:
        if not isinstance(row, dict): continue
        key = row.get('id')
        if key and (key not in dedup or row['score'] > dedup[key]['score']):
            dedup[key] = row
    return sorted(dedup.values(), key=lambda x: (-x['score'], x['source'], x['id']))[:limit]

def mission_for(item):
    if item['category'] == 'empleo_remoto':
        return f"Verificar requisitos y ubicación de «{item['title'][:80]}». Si encaja, preparar candidatura para revisión humana."
    return f"Leer la conversación original y comprobar si «{item['title'][:65]}» implica un encargo pagado y abierto."

def get_ai_brief(items, fetch=fetch_json):
    # Credentials alone never authorize spending.
    return {"state": "no_configurado", "text": "IA de pago desactivada: requiere autorización y control de costes; no se realizan llamadas."}

def collect(fetch=fetch_json, include_ai=True):
    now = dt.datetime.now(UTC).isoformat(timespec='seconds')
    results, audits = [], []
    sources = [('Jobicy Europa', lambda: get_jobicy('europe', fetch)),
               ('Jobicy worldwide', lambda: get_jobicy('anywhere', fetch)),
               ('HN freelance', lambda: get_hn('freelance', fetch)),
               ('HN contract', lambda: get_hn('contract', fetch))]
    source_urls = ['https://jobicy.com/api/jobs?count=100&geo=europe',
                   'https://jobicy.com/api/jobs?count=100&geo=anywhere',
                   'https://hn.algolia.com/api/v1/search_by_date?query=freelance&tags=comment&hitsPerPage=100',
                   'https://hn.algolia.com/api/v1/search_by_date?query=contract&tags=comment&hitsPerPage=100']
    for (name, fn), source_url in zip(sources, source_urls):
        try:
            found = fn()
            results.extend(found)
            audits.append({'name': name, 'url': source_url, 'observed_at': now, 'state': 'ok', 'count': len(found), 'error': None})
        except Exception as exc:
            # Errors are visible, no fabricated successes.
            audits.append({'name': name, 'url': source_url, 'observed_at': now, 'state': 'error', 'count': 0,
                           'error': type(exc).__name__ + ': consulta pública fallida'})
    picks = unique_ranked(results)
    if include_ai:
        try: brief = get_ai_brief(picks)
        except Exception as exc: brief = {'state': 'error', 'text': 'Error de API de IA: ' + type(exc).__name__}
    else: brief = {'state': 'desactivado', 'text': 'La IA generativa no se ha ejecutado.'}
    missions = [{'agent': item['agent'], 'title': item['title'][:95], 'task': mission_for(item),
                 'source_id': item['id'], 'url': item['url'], 'state': 'pendiente_de_revision'}
                for item in picks[:6]]
    return {
        'schema_version': 3, 'last_run_utc': now, 'run_type': 'recoleccion_publica',
        'run_result': 'completo' if all(a['state']=='ok' for a in audits) else
                      ('parcial' if any(a['state']=='ok' for a in audits) else 'fallido'),
        'sources': audits, 'opportunities': picks, 'missions': missions,
        'ai_brief': brief,
        'facts': {'confirmed_revenue_eur': None, 'confirmed_profit_eur': None,
                  'sales_completed': None, 'payments_verified': False,
                  'notice': 'No hay cuentas bancarias conectadas; sin verificación de cobros.'},
        'policy': 'No compras, contactos, publicaciones ni inversión sin aprobación expresa.'
    }
