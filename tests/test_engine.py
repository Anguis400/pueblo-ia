import unittest
import json
import tempfile
import pathlib
from app.engine import collect, get_hn, get_jobicy, plain, score, unique_ranked, safe_url
from app.render import render
from unittest.mock import patch

class EngineTests(unittest.TestCase):
    def example_fetch(self, url):
        if 'jobicy' in url:
            return {'jobs':[{'id':101,'jobTitle':'Python Excel Automation Analyst',
                     'companyName':'Ejemplo de test (NO REAL)',
                     'jobGeo':'Europe','jobDescription':'Help us automate spreadsheets and dashboards.',
                     'url':'https://jobicy.com/jobs/test-placeholder', 'pubDate':'2026-11-14T12:00:00Z'}]}
        return {'hits':[]}

    def test_clean_html(self):
        self.assertEqual(plain('<p>Oferta <b>concreta</b></p>'), 'Oferta concreta')
        self.assertGreater(score('Python Excel Automation'), 4)

    def test_url_allowlist(self):
        self.assertIsNone(safe_url('javascript:alert(1)', {'jobicy.com'}))
        self.assertIsNone(safe_url('https://jobicy.com.evil.example/jobs', {'jobicy.com'}))
        self.assertIsNotNone(safe_url('https://jobicy.com/jobs/x', {'jobicy.com'}))

    def test_jobicy_fixture_not_real(self):
        rows=get_jobicy(fetch=self.example_fetch)
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]['revenue_eur'])
        self.assertEqual(rows[0]['category'], 'empleo_remoto')

    def test_collect_no_model_no_money(self):
        with patch.dict('os.environ', {}, clear=True):
            s=collect(fetch=self.example_fetch)
        self.assertEqual(s['run_result'], 'completo')
        self.assertEqual(len(s['opportunities']),1)  # same Jobicy item deduplicated
        self.assertIsNone(s['facts']['confirmed_revenue_eur'])
        self.assertFalse(s['facts']['payments_verified'])
        self.assertEqual(s['ai_brief']['state'], 'no_configurado')

    def test_fail_all_sources_visibility(self):
        def bad(url): raise OSError('offline')
        s=collect(fetch=bad,include_ai=False)
        self.assertEqual(s['run_result'],'fallido')
        self.assertEqual(len(s['sources']),4)
        self.assertTrue(all(x['state']=='error' for x in s['sources']))

    def test_template_escaped(self):
        with tempfile.TemporaryDirectory() as directory:
            # Render is unit tested by reading actual template and inspecting generated page in a temp root.
            import app.render as r
            original=r.ROOT
            root=pathlib.Path(directory)
            (root/'site').mkdir()
            (root/'web').mkdir()
            (root/'web'/'template.html').write_text('<h1>Ok</h1><!-- VILLAGE_SNAPSHOT -->',encoding='utf-8')
            try:
                r.ROOT=root
                r.render({'untrusted':'</script><img src=x onerror=alert(1)>'})
                body=(root/'site'/'index.html').read_text(encoding='utf-8')
                self.assertNotIn('</script><img',body)
                self.assertIn('\\u003c',body)
            finally: r.ROOT=original

if __name__=='__main__': unittest.main()
