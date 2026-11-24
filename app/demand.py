"""Read public Workana requests. No accounts, messages, bids or paid APIs."""
import datetime as dt
import html
import json
import re
import unicodedata
import urllib.parse
import urllib.request
from html.parser import HTMLParser

UTC = dt.timezone.utc
MAX_AGE_DAYS = 30
WATCHED_REQUEST = 'https://www.workana.com/job/desenvolvimento-de-planilha-financeira-e-de-custos-para-confeitaria'
SEARCHES = [('escandallos', 'escandallo'), ('costes', 'costos'),
            ('custos para confeitaria', 'custos confeitaria'),
            ('planilhas para confeitaria', 'planilha confeitaria')]


def fetch_html(url):
    if not project_url(url) and not url.startswith('https://www.workana.com/jobs?'):
        raise ValueError('Only public Workana project/search pages are allowed')
    request = urllib.request.Request(url, headers={
        'User-Agent': 'PuebloIA-Research/1.0 (public project research)',
        'Accept': 'text/html',
    })
    with urllib.request.urlopen(request, timeout=18) as response:
        if urllib.parse.urlparse(response.url).hostname != 'www.workana.com':
            raise ValueError('Unexpected redirect')
        data = response.read(1800001)
    if len(data) > 1800000:
        raise ValueError('Source exceeds size limit')
    return data.decode('utf-8')


def project_url(url):
    parsed = urllib.parse.urlparse(str(url))
    if (parsed.scheme != 'https' or parsed.netloc != 'www.workana.com'
            or parsed.query or parsed.fragment):
        return None
    if not re.fullmatch(r'/(?:es/|en/|pt/)?job/[a-z0-9][a-z0-9-]{4,230}', parsed.path):
        return None
    return 'https://www.workana.com/job/' + parsed.path.rsplit('/', 1)[1]


def folded(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))


def relevant_request(text):
    body = folded(text)
    sector = re.search(r'pasteler|reposter|panader|obrador|confeitar|padaria|bakery|baking|restaurant|catering', body)
    costing = re.search(r'cost[eoas]|\bcustos?\b|escandall|precifica|pricing', body)
    tool = re.search(r'excel|planilh|planilla|spreadsheet|calculador|software|sistema|herramienta|automatiza', body)
    return bool(sector and costing and tool)


class SearchResults(HTMLParser):
    def __init__(self):
        super().__init__()
        self.payload = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'search' and ':results-initials' in attrs:
            self.payload = json.loads(attrs[':results-initials'])


def search_candidates(raw):
    from .engine import plain
    parser = SearchResults()
    parser.feed(raw)
    data = parser.payload
    if not isinstance(data, dict) or not isinstance(data.get('results'), list):
        raise ValueError('Workana search schema unavailable')
    if not data['results'] and data.get('resultDescription', {}).get('count') != 0:
        raise ValueError('Workana search results incomplete')
    urls = []
    for row in data['results']:
        if not isinstance(row, dict):
            continue
        body = plain(str(row.get('title', '')) + ' ' + str(row.get('description', '')))
        if not relevant_request(body):
            continue
        # The listing exposes its project link inside the title, not in row.url.
        match = re.search(r'href=[\"\']([^\"\']+)', str(row.get('title', '')))
        link = project_url(urllib.parse.urljoin('https://www.workana.com', html.unescape(match[1]))) if match else None
        if link and link not in urls:
            urls.append(link)
    return urls[:3]


MONTHS = {name: number for number, names in enumerate([
    'january enero janeiro', 'february febrero fevereiro', 'march marzo marco',
    'april abril', 'may mayo maio', 'june junio junho', 'july julio julho',
    'august agosto', 'september septiembre setembro', 'october octubre outubro',
    'november noviembre novembro', 'december diciembre dezembro',
], 1) for name in names.split()}


def published_date(header):
    text = folded(header)
    for month, number in MONTHS.items():
        match = re.search(r'\b' + month + r'\s+(\d{1,2}),?\s+(\d{4})\b', text)
        if match:
            return dt.date(int(match[2]), number, int(match[1]))
        match = re.search(r'\b(\d{1,2})\s+(?:de\s+)?' + month + r',?\s+(?:de\s+)?(\d{4})\b', text)
        if match:
            return dt.date(int(match[2]), number, int(match[1]))
    raise ValueError('Project publication date unavailable')


def parse_project(raw, url, now=None):
    from .engine import plain
    link = project_url(url)
    if not link:
        raise ValueError('Invalid project URL')
    now = now or dt.datetime.now(UTC)
    header = re.search(r'<header\b[^>]*id=[\"\']productName[\"\'][^>]*>(.*?)</header>', raw, re.S | re.I)
    if not header:
        raise ValueError('Project header unavailable')
    status = re.search(r'<span\b[^>]*>(.*?)</span>', header[1], re.S | re.I)
    if not status:
        raise ValueError('Project status unavailable')
    # Use the main status. Closed pages can also contain an unrelated "Open" heading.
    state = folded(plain(status[1]))
    if state not in ('evaluating bids', 'evaluando propuestas', 'avaliando propostas', 'open', 'abierto', 'aberto'):
        return None
    published = published_date(plain(header[1]))
    if not 0 <= (now.date() - published).days <= MAX_AGE_DAYS:
        return None
    title_match = re.search(r'<h1\b[^>]*>(.*?)</h1>', header[1], re.S | re.I)
    if not title_match:
        raise ValueError('Project title unavailable')
    title = plain(title_match[1])[:180]
    # Read only the project description area, before client/profile sections.
    description_match = re.search(r'<div\b[^>]*\bv-wk-expandable\b[^>]*>(.*?)</div>', raw, re.S | re.I)
    if not description_match:
        raise ValueError('Project description unavailable')
    description = plain(description_match[1])
    if not relevant_request(title + ' ' + description):
        return None
    observed = now.isoformat(timespec='seconds')
    return {
        'id': 'workana-' + link.rsplit('/', 1)[1], 'agent': 'sales',
        'source': 'Workana / petición pública', 'category': 'posible_encargo_no_verificado',
        'title': title, 'company': '', 'region': 'Sin verificar', 'url': link,
        'published': published.isoformat(), 'observed_at': observed,
        'excerpt': description[:320], 'score': 15,
        'status': 'Petición pública de herramienta de costes; presupuesto, acceso y contratación pendientes de verificar',
        'project_status_observed': state, 'budget_eur': None,
        'revenue_eur': None, 'expense_eur': None,
    }


def search_workana(query, fetch=fetch_html):
    url = 'https://www.workana.com/jobs?' + urllib.parse.urlencode({'query': query})
    rows = [parse_project(fetch(link), link) for link in search_candidates(fetch(url))]
    return [row for row in rows if row is not None]


def watch_request(fetch=fetch_html):
    row = parse_project(fetch(WATCHED_REQUEST), WATCHED_REQUEST)
    return [row] if row else []
