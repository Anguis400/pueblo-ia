import hashlib
import json
import pathlib
import subprocess
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from app.company import build_company, policy, DEPARTMENTS
from app.engine import collect, get_ai_brief, plain
from app.products import PRODUCTS


class CompanyTests(unittest.TestCase):
    def snapshot(self):
        return collect(fetch=lambda url: {'jobs': []} if 'jobicy' in url else {'hits': []}, include_ai=False)

    def test_roles_evidence_and_safe_pages(self):
        snapshot = self.snapshot()
        snapshot['opportunities'] = [{'id': 'hn-123', 'category': 'posible_encargo_no_verificado', 'title': '</summary><script>alert(1)</script>', 'excerpt': 'python', 'url': 'https://news.ycombinator.com/item?id=123', 'score': 9}]
        with tempfile.TemporaryDirectory() as directory:
            site = pathlib.Path(directory)
            report = build_company(snapshot, site)
            self.assertEqual(len(report['agents']), 21)
            self.assertEqual(len(DEPARTMENTS), 7)
            self.assertEqual(len(set(a['agent'] for a in report['agents'])), 21)
            for a in report['agents']:
                artifact = json.loads((site / a['evidence']).read_text())
                self.assertEqual(artifact['agent'], a['agent'])
                self.assertEqual(artifact['time_utc'], snapshot['last_run_utc'])
            page = (site / 'marketing/index.html').read_text()
            self.assertNotIn('<script>alert', page)
            self.assertIn('&lt;script&gt;', page)
            self.assertIsNone(report['finances']['verified_net_profit_eur'])
            self.assertIsNone(report['finances']['proposed_reinvestment_eur'])
            self.assertEqual(report['finances']['automated_spend_this_run_eur'], 0)
            for p in report['catalog']:
                payload = (site / p['url']).read_bytes()
                self.assertEqual(hashlib.sha256(payload).hexdigest(), p['sha256'])
                with zipfile.ZipFile(site / p['download']) as archive:
                    self.assertEqual(archive.read('index.html'), payload)
            old_paths = {p.relative_to(site): p.read_bytes() for p in site.glob('data/company/*/*.json')}
            snapshot['last_run_utc'] = '2026-11-15T00:00:00+00:00'
            build_company(snapshot, site)
            for path, content in old_paths.items():
                self.assertEqual((site / path).read_bytes(), content)

    def test_no_fake_proposals_or_clients(self):
        with tempfile.TemporaryDirectory() as directory:
            report = build_company(self.snapshot(), pathlib.Path(directory))
            agents = {a['agent']: a for a in report['agents']}
            self.assertEqual(agents['propuestas']['result']['drafts'], [])
            self.assertEqual(agents['propuestas']['state'], 'pendiente')
            self.assertIsNone(agents['conversion']['result']['verified_sales'])
            self.assertEqual(agents['competencia']['state'], 'pendiente')
            self.assertEqual(agents['contenido']['state'], 'preparado')
            self.assertEqual(agents['conversion']['state'], 'bloqueado')
            self.assertEqual(agents['tesoreria']['state'], 'bloqueado')
            calendar = agents['contenido']['result']['calendar']
            self.assertEqual(len(calendar), 1)
            self.assertEqual(calendar[0]['demo'], 'tienda/escandallo-pro/')
            self.assertNotIn('Shopify', str(agents['conversion']['result']))

    def test_daily_limit(self):
        import datetime as dt
        from app.run import daily_limit_reached
        now = dt.datetime(2026, 11, 14, tzinfo=dt.timezone.utc)
        rows = [{"time_utc": "2026-11-14T00:00:00Z"}] * 8
        self.assertTrue(daily_limit_reached(rows, now))
        self.assertFalse(daily_limit_reached(rows[:7], now))
        self.assertFalse(daily_limit_reached(rows, now + dt.timedelta(days=1)))

    def test_policy_fail_closed(self):
        value = policy()
        for key in ('paid_ai_enabled', 'paid_ads_enabled', 'automated_outreach_enabled'):
            with patch('app.company.json.loads', return_value={**value, key: True}):
                with self.assertRaises(ValueError): policy()

    def test_paid_ai_never_calls_even_with_credentials(self):
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'fake', 'OPENAI_MODEL': 'fake'}):
            with patch('urllib.request.urlopen', side_effect=AssertionError('Network forbidden')):
                self.assertEqual(get_ai_brief([])['state'], 'no_configurado')

    def test_public_contact_and_credentials_redacted(self):
        text = plain('Contact me at person@example.com or +34 612 345 678 token sk-abcdefghijklmnopqrst')
        for private in ('person@example.com', '612 345 678', 'sk-abcdefghijklmnopqrst'):
            self.assertNotIn(private, text)

    @unittest.skipUnless(__import__('shutil').which('node'), 'Node used for JavaScript calculation tests')
    def test_real_javascript_calculations(self):
        formulas = {p[0]: p[4] for p in PRODUCTS}
        script = 'const money=n=>n.toFixed(2);\n'
        cases = [
            ('escandallo', {'coste': 10, 'horas': 2, 'tarifa': 20, 'margen': 50}, '100.00'),
            ('presupuesto', {'horas': 2, 'tarifa': 20, 'extras': 10, 'impuesto': 21}, '60.50'),
            ('rentabilidad', {'fijos': 100, 'variable': 5, 'precio': 15}, '10'),
            ('conversion', {'visitas': 100, 'consultas': 10, 'ventas': 2}, '2.00%'),
        ]
        for key, value, expected in cases:
            script += f'if(!(function(v){{{formulas[key]}}})({json.dumps(value)}).includes({json.dumps(expected)}))throw Error({json.dumps(key)});\n'
        script += f'for(const v of [{{precio:5,variable:5,fijos:1}},{{precio:4,variable:5,fijos:1}}]){{let failed=false;try{{(function(v){{{formulas["rentabilidad"]}}})(v)}}catch(e){{failed=true}}if(!failed)throw Error("missing validation")}}'
        subprocess.run(['node', '-e', script], check=True, capture_output=True)
