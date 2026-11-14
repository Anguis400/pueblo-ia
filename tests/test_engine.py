import unittest
import json
import tempfile
import pathlib
from app.engine import collect, get_hn, get_jobicy, plain, score, unique_ranked, safe_url, buyer_intent
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

    def test_buyer_intent_excludes_profiles(self):
        self.assertFalse(buyer_intent('Location: Pakistan Remote: Yes Willing to relocate: No Technologies: Python, Excel. I am a freelancer.'))
        self.assertFalse(buyer_intent('SEEKING WORK - I am looking for freelance work using Python and spreadsheets.'))
        self.assertFalse(buyer_intent('Available for hire. Python Excel freelance contractor.'))
        self.assertTrue(buyer_intent('We are looking to hire a Python freelancer to build an Excel dashboard. Budget: $300.'))
        self.assertTrue(buyer_intent('I need help with Power BI dashboard automation. Can someone build it?'))

    def test_hn_returns_buyer_not_seller(self):
        import datetime as dt
        ts=dt.datetime.now(dt.timezone.utc).isoformat()
        samples=[
            {'objectID': '32111', 'created_at': ts, 'comment_text': 'Location: Pakistan Remote: Yes Willing to relocate: No Technologies: Python Excel freelance contractor looking for work'},
            {'objectID': '32112', 'created_at': ts, 'comment_text': 'We are looking to hire a Python contractor to automate Excel spreadsheets. Budget $300'},
            {'objectID': '32113', 'created_at': ts, 'comment_text': 'I am looking for freelance projects using Excel and Python'},
        ]
        result=get_hn(fetch=lambda url: {'hits': samples})
        self.assertEqual([row['id'] for row in result], ['hn-32112'])
        self.assertEqual(result[0]['revenue_eur'], None)

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
                body=(root/'site'/'radar'/'index.html').read_text(encoding='utf-8')
                self.assertNotIn('</script><img',body)
                self.assertIn('\\u003c',body)
            finally: r.ROOT=original

if __name__=='__main__': unittest.main()
