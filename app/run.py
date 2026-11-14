import json
import pathlib
from .engine import collect
from .render import render
ROOT = pathlib.Path(__file__).resolve().parents[1]

def main():
    root = ROOT / 'site'
    (root / 'data').mkdir(parents=True, exist_ok=True)
    snapshot = collect()
    (root / 'data' / 'latest.json').write_text(json.dumps(snapshot, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    # history stores only publicly sourced lead IDs and execution summary; no finances or secrets
    history_path = root / 'data' / 'runs.json'
    try: history = json.loads(history_path.read_text(encoding='utf-8'))
    except (FileNotFoundError, ValueError): history = []
    history.append({'time_utc': snapshot['last_run_utc'], 'result': snapshot['run_result'],
                    'sources': snapshot['sources'], 'lead_count': len(snapshot['opportunities']),
                    'ai_state': snapshot['ai_brief']['state']})
    history = history[-150:]
    history_path.write_text(json.dumps(history, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    render(snapshot)
    print(json.dumps({'run_result': snapshot['run_result'], 'leads': len(snapshot['opportunities']),
                      'sources': snapshot['sources'], 'ai_state': snapshot['ai_brief']['state']},ensure_ascii=False))
    # Fail the job if ALL sources failed so that a green build is never falsely reported.
    if snapshot['run_result'] == 'fallido': raise SystemExit('All sources failed; see log')

if __name__ == '__main__': main()
