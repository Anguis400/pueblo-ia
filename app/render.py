"""Safely embed a JSON snapshot in a no-framework static village dashboard."""
import json
import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]

def render(snapshot):
    template = (ROOT / 'web' / 'template.html').read_text(encoding='utf-8')
    json_text = json.dumps(snapshot, ensure_ascii=False).replace('<','\\u003c').replace('&','\\u0026')
    if '<!-- VILLAGE_SNAPSHOT -->' not in template:
        raise ValueError('Template snapshot marker missing')
    page = template.replace('<!-- VILLAGE_SNAPSHOT -->',
                            '<script type="application/json" id="village-snapshot">' + json_text + '</script>')
    (ROOT / 'site' / 'index.html').write_text(page, encoding='utf-8')

if __name__ == '__main__':
    root=ROOT/'site'/'data'/'latest.json'
    render(json.loads(root.read_text(encoding='utf-8')))
