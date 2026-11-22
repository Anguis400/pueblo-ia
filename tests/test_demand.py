"""Synthetic fixtures: never buyer records or simulated sales."""
import datetime as dt
import html
import json
import unittest
from unittest.mock import patch

from app.demand import (WATCHED_REQUEST, parse_project, project_url,
                        relevant_request, search_candidates, search_workana)
from app.engine import collect

NOW = dt.datetime(2026, 11, 23, tzinfo=dt.timezone.utc)
URL = 'https://www.workana.com/job/fixture-costes-obrador-no-real'


def project(status='Evaluating bids', date='November 20, 2026', body=None):
    body = body or 'Necesito una herramienta Excel de costes para mi pastelería. Ingredientes y recetas.'
    return (f'<header id="productName"><span class="open">{status}</span>'
            f'<h1>Fixture de costes para pastelería (NO REAL)</h1><p>Published on the {date}</p></header>'
            f'<h4>Open</h4><div class="expander" v-wk-expandable>{body}</div>')


def listing(rows=None):
    rows = rows or []
    payload = {'resultDescription': {'count': len(rows)}, 'results': rows}
    return '<search :results-initials="' + html.escape(json.dumps(payload), quote=True) + '"></search>'


def empty_fetch(url):
    if '/jobs?' in url:
        return listing()
    return project(status='Finished')


class DemandTests(unittest.TestCase):
    def test_closed_header_overrides_unrelated_open_heading(self):
        for state in ('Finished', 'Finalizado', 'Cancelled', 'Finalizado / Closed'):
            self.assertIsNone(parse_project(project(status=state), URL, NOW))

    def test_requires_recent_absolute_date(self):
        for date in ('October 01, 2026', 'November 24, 2026'):
            self.assertIsNone(parse_project(project(date=date), URL, NOW))
        with self.assertRaises(ValueError):
            parse_project(project(date='hace unas semanas'), URL, NOW)
        row = parse_project(project(date='20 de Novembro de 2026'), URL, NOW)
        self.assertEqual(row['published'], '2026-11-20')

    def test_budget_and_revenue_stay_unknown_and_contacts_redacted(self):
        row = parse_project(project(body='Necesito Excel para costes de pastelería. Escribe a test@example.com o +34 612 345 678.'), URL, NOW)
        self.assertIsNone(row['revenue_eur'])
        self.assertIsNone(row['budget_eur'])
        self.assertEqual(row['category'], 'posible_encargo_no_verificado')
        self.assertNotIn('test@example.com', row['excerpt'])
        self.assertNotIn('612 345 678', row['excerpt'])

    def test_precision_rejects_generic_work_and_non_tool_jobs(self):
        self.assertFalse(relevant_request('Buscamos un ingeniero Python remoto para automatizar Excel'))
        self.assertFalse(relevant_request('Buscamos pastelero para cocinar y controlar costes'))
        self.assertTrue(relevant_request('Planilha de custos e precificação para confeitaria'))
        self.assertTrue(relevant_request('Software de escandallos para obrador'))

    def test_allowlist_and_canonical_dedup(self):
        self.assertEqual(project_url(URL.replace('/job/', '/pt/job/')), URL)
        for url in ('https://www.workana.com.evil.test/job/fixture-costes',
                    'https://www.workana.com@evil.test/job/fixture-costes',
                    URL + '?auth=secret', 'http://www.workana.com/job/fixture-costes'):
            self.assertIsNone(project_url(url))

    def test_public_search_reads_only_relevant_project_links(self):
        rows = [{'title': '<a href="/job/fixture-costes-obrador-no-real">Excel costes pastelería</a>', 'description': 'Necesito una calculadora de costes'}]
        rows += [rows[0].copy(), {'title': '<a href="https://evil.test/job/x">Excel costes pastelería</a>', 'description': 'costes'}]
        rows += [{'title': '<a href="/job/irrelevante-no-real">Trabajo remoto Python</a>', 'description': 'Excel software'}]
        self.assertEqual(search_candidates(listing(rows)), [URL])

    def test_missing_source_schema_is_error_not_empty_success(self):
        for raw in ('<html>Login</html>', '<search :results-initials="{}"></search>'):
            with self.assertRaises(ValueError):
                search_candidates(raw)
        with self.assertRaises(ValueError):
            search_candidates('<search :results-initials=\'{"resultDescription":{"count":10},"results":[]}\'></search>')
        self.assertEqual(search_candidates(listing()), [])

    def test_collect_does_not_query_legacy_jobs_or_fabricate_results(self):
        seen = []
        def fetch(url):
            seen.append(url)
            return empty_fetch(url)
        snapshot = collect(fetch=fetch, include_ai=False)
        self.assertEqual(snapshot['run_result'], 'completo')
        self.assertEqual(snapshot['opportunities'], [])
        self.assertEqual(len(snapshot['sources']), 3)
        self.assertTrue(all('workana.com' in url for url in seen))
        self.assertIsNone(snapshot['facts']['confirmed_revenue_eur'])

    def test_detail_parse_failure_marks_source_error(self):
        def broken(url):
            if url == WATCHED_REQUEST:
                return '<html>Site unavailable</html>'
            return listing()
        snapshot = collect(fetch=broken, include_ai=False)
        self.assertEqual(snapshot['run_result'], 'parcial')
        self.assertEqual(snapshot['sources'][-1]['state'], 'error')


if __name__ == '__main__':
    unittest.main()
