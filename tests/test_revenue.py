"""The sales queue must never promote a draft, stale lead or test order to revenue."""
import copy
import datetime as dt
import json
import pathlib
import tempfile
import unittest
from app.revenue import build_pipeline, prepare_sales, render_sales

NOW = '2026-11-24T10:00:00+00:00'
URL = 'https://www.workana.com/job/fixture-confeitaria-no-real'


def snapshot():
    return {'last_run_utc': NOW, 'run_result': 'completo', 'opportunities': [
        {'id': 'workana-fixture-confeitaria-no-real', 'title': 'Planilha de custos para confeitaria (FIXTURE, NO REAL)',
         'excerpt': 'Planilha Excel de ingredientes, receitas e projeções financeiras para confeitaria.',
         'category': 'posible_encargo_no_verificado', 'published': '2026-11-20',
         'observed_at': NOW, 'project_status_observed': 'evaluating bids', 'url': URL}]}


class RevenueTests(unittest.TestCase):
    def test_specific_consultation_admits_product_gap_without_commitments(self):
        result = build_pipeline(snapshot(), prepared_at=NOW)
        self.assertEqual(len(result['requests']), 1)
        draft = result['requests'][0]['draft']
        self.assertEqual(draft['language'], 'pt')
        self.assertIn('não uma planilha Excel', draft['text'])
        self.assertEqual(len(draft['capability_gaps']), 2)
        self.assertIsNone(draft['price_eur'])
        self.assertIsNone(draft['delivery_commitment'])
        self.assertIsNone(draft['sent_at'])
        self.assertIsNone(result['experiment']['started_at'])
        self.assertIsNone(result['metrics']['verified_paid_orders'])
        self.assertIsNone(result['metrics']['verified_net_profit_eur'])
        self.assertEqual(result['metrics']['messages_sent_by_this_run'], 0)

    def test_closed_stale_missing_date_or_generic_jobs_do_not_prepare_contacts(self):
        for update in [{'project_status_observed': 'Finished'}, {'published': '2026-09-01'},
                       {'published': '2026-11-25'}, {'published': None},
                       {'excerpt': 'General Excel work', 'title': 'Python job'},
                       {'url': 'https://evil.example/project'}, {'category': 'empleo_remoto'}]:
            with self.subTest(update=update):
                sample = snapshot()
                sample['opportunities'][0].update(update)
                self.assertEqual(build_pipeline(sample, prepared_at=NOW)['requests'], [])

    def test_same_request_is_deduplicated_across_languages_and_rounds(self):
        sample = snapshot()
        duplicate = copy.deepcopy(sample['opportunities'][0])
        duplicate['url'] = URL.replace('/job/', '/pt/job/')
        sample['opportunities'].append(duplicate)
        first = build_pipeline(sample, prepared_at=NOW)
        self.assertEqual(len(first['requests']), 1)
        second = build_pipeline(sample, first, '2026-11-25T10:00:00+00:00')
        self.assertTrue(second['requests'][0]['known_to_pipeline'])
        self.assertEqual(second['requests'][0]['tracking_started_at'], NOW)
        self.assertEqual(second['metrics']['messages_sent_by_this_run'], 0)
        self.assertIsNone(second['experiment']['started_at'])

    def test_disappearing_request_is_not_reported_as_customer_or_rejection(self):
        first = build_pipeline(snapshot(), prepared_at=NOW)
        empty = {**snapshot(), 'opportunities': []}
        second = build_pipeline(empty, first, NOW)
        self.assertEqual(second['requests'], [])
        self.assertEqual(second['no_longer_in_round'], [first['requests'][0]['id']])
        self.assertIsNone(second['metrics']['customer_replies'])

    def test_future_research_is_rejected(self):
        with self.assertRaises(ValueError):
            build_pipeline(snapshot(), prepared_at='2026-11-23T00:00:00+00:00')

    def test_corrupt_queue_is_not_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            (root / 'data').mkdir()
            file = root / 'data/sales.json'
            file.write_text('{broken')
            with self.assertRaises(ValueError):
                prepare_sales(snapshot(), root, NOW)
            self.assertEqual(file.read_text(), '{broken')

    def test_page_escapes_untrusted_draft_and_rejects_active_links(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            model = prepare_sales(snapshot(), root, NOW)
            row = model['requests'][0]
            row['draft']['text'] = '</blockquote><script>alert(1)</script>'
            row['source_url'] = 'javascript:alert(2)'
            (root / 'data/sales.json').write_text(json.dumps(model))
            render_sales(root)
            page = (root / 'ventas/index.html').read_text()
            self.assertNotIn('<script>', page)
            self.assertIn('&lt;script&gt;', page)
            self.assertNotIn('href="javascript:', page)
            self.assertIn('noindex', page)
