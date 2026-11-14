"""Verify that the visual layer preserves evidence and unknown/zero semantics."""
import copy
import hashlib
import json
import pathlib
import tempfile
import unittest
from html.parser import HTMLParser
from unittest.mock import patch

from app.presentation import render_company, state_key, view_model, local_url

ROOT = pathlib.Path(__file__).resolve().parents[1]


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids = []
        self.links = []
        self.buildings = []
        self.scripts = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'a':
            self.links.append(attrs.get('href', ''))
            if 'building' in attrs.get('class', '').split():
                self.buildings.append(attrs.get('data-department'))
        if tag == 'script':
            self.scripts.append(attrs.get('src'))


class PresentationTests(unittest.TestCase):
    def setUp(self):
        self.report = json.loads((ROOT / 'site/data/company.json').read_text(encoding='utf-8'))

    def test_kpis_are_derived_and_zero_is_not_unknown(self):
        report = copy.deepcopy(self.report)
        report['catalog'].append({'state': 'pendiente'})
        for agent in report['agents']:
            if agent['agent'] == 'demanda':
                agent['result']['buyer_signals'] = 7
            if agent['agent'] == 'conversion':
                agent['result']['verified_sales'] = 0
        report['finances']['automated_spend_this_run_eur'] = None
        model = view_model(report)
        self.assertEqual(model['products'], 4)
        self.assertEqual(model['buyers'], 7)
        self.assertEqual(model['sales'], 0)
        self.assertIsNone(model['spend'])
        self.assertIsNone(model['reinvestment_amount'])
        for agent in report['agents']:
            if agent['agent'] == 'conversion':
                agent['result']['verified_sales'] = None
        self.assertIsNone(view_model(report)['sales'])

    def test_department_status_does_not_hide_a_blocked_role(self):
        model = view_model(self.report)
        self.assertEqual(len(model['departments']), 7)
        departments = {d['id']: d for d in model['departments']}
        self.assertEqual(departments['marketing']['state'], 'bloqueado')
        self.assertEqual(departments['producto']['state'], 'completado')
        self.assertEqual(state_key('preparado; posicionamiento no medido'), 'preparado')
        self.assertEqual(state_key('actividad no reconocida'), 'desconocido')
        partial = copy.deepcopy(self.report)
        partial['agents'][3]['state'] = 'error'
        self.assertEqual(view_model(partial)['departments'][1]['state'], 'error')

    def test_render_is_read_only_for_reports_and_existing_deliverables(self):
        before = copy.deepcopy(self.report)
        with tempfile.TemporaryDirectory() as directory:
            site = pathlib.Path(directory)
            fixtures = {'data/runs.json': b'[]\n', 'data/company.json': b'{"sentinel":true}',
                        'data/company/old/report.json': b'{"history":1}',
                        'tienda/escandallo.html': b'original demo', 'tienda/escandallo.zip': b'original ZIP'}
            for path, content in fixtures.items():
                target = site / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            with patch('urllib.request.urlopen', side_effect=AssertionError('Presentation must not fetch')):
                render_company(self.report, site)
            for path, content in fixtures.items():
                self.assertEqual((site / path).read_bytes(), content)
            self.assertEqual(self.report, before)
            for path in ('index.html', 'empresa/index.html', 'marketing/index.html', 'tienda/index.html', 'assets/pueblo.css', 'assets/pueblo.js'):
                self.assertTrue((site / path).is_file())

    def test_role_ids_evidence_and_relative_pages_links(self):
        with tempfile.TemporaryDirectory() as directory:
            site = pathlib.Path(directory)
            render_company(self.report, site)
            for route, prefix in [('index.html', ''), ('empresa/index.html', '../')]:
                doc = Document((site / route).read_text())
                self.assertEqual(len(doc.buildings), 7)
                self.assertEqual(len(doc.ids), len(set(doc.ids)))
                for role in self.report['agents']:
                    self.assertIn(role['agent'], doc.ids)  # v3 deep links survive
                    self.assertIn(prefix + role['evidence'], doc.links)
                for destination in ('empresa/', 'marketing/', 'tienda/', 'radar/'):
                    self.assertIn(prefix + destination, doc.links)
                self.assertEqual(doc.scripts, [prefix + 'assets/pueblo.js'])
            shop = (site / 'tienda/index.html').read_text()
            for product in self.report['catalog']:
                self.assertIn('href="../' + product['url'] + '"', shop)
                self.assertIn('href="../' + product['download'] + '" download', shop)
            self.assertIn('Escandallo Pro', shop)
            self.assertIn('herramienta independiente', shop)

    def test_untrusted_text_and_evidence_urls_cannot_become_markup(self):
        report = copy.deepcopy(self.report)
        malicious = '</summary><script>alert(1)</script><img src=x onerror=alert(2)>'
        report['agents'][0]['result']['priority'] = malicious
        report['agents'][0]['name'] = malicious
        report['agents'][0]['evidence'] = 'javascript:alert(3)'
        with tempfile.TemporaryDirectory() as directory:
            site = pathlib.Path(directory)
            render_company(report, site)
            page = (site / 'empresa/index.html').read_text()
            self.assertNotIn(malicious, page)
            self.assertIn('&lt;script&gt;alert(1)', page)
            self.assertNotIn('href="javascript:', page)
            self.assertNotIn('href="//', page)
        for url in ['//evil.example', 'javascript:alert(1)', '../secrets', '/admin', 'data/x?token=a', 'data/../../secret']:
            self.assertIsNone(local_url(url, '../'))

    def test_saved_product_hashes_still_match_actual_demos(self):
        for product in self.report['catalog']:
            self.assertEqual(hashlib.sha256((ROOT / 'site' / product['url']).read_bytes()).hexdigest(), product['sha256'])


if __name__ == '__main__':
    unittest.main()
