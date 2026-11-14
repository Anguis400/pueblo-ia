"""Scheduled, zero-spend research and deterministic company build."""
import datetime as dt
import json
import pathlib
from .engine import collect
from .render import render
from .company import build_company, policy
ROOT = pathlib.Path(__file__).resolve().parents[1]


def daily_limit_reached(history, now):
    return sum(row.get("time_utc", "")[:10] == now.date().isoformat() for row in history) >= 8


def main():
    policy()  # fail closed before any network activity
    root = ROOT / 'site'
    (root / 'data').mkdir(parents=True, exist_ok=True)
    history_path = root / 'data/runs.json'
    try:
        history = json.loads(history_path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        history = []
    if not isinstance(history, list):
        raise ValueError('Invalid history; refusing to overwrite')
    if daily_limit_reached(history, dt.datetime.now(dt.timezone.utc)):
        print("Límite de 8 rondas UTC/día alcanzado; se conserva la última evidencia sin nuevas consultas.")
        return
    snapshot = collect(include_ai=False)
    report = build_company(snapshot, root)
    archive = root / 'data/snapshots'
    archive.mkdir(exist_ok=True)
    (archive / (report['run_id'] + '.json')).write_text(json.dumps(snapshot, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    (root / 'data/latest.json').write_text(json.dumps(snapshot, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    history.append({'time_utc': snapshot['last_run_utc'], 'result': snapshot['run_result'],
                    'sources': snapshot['sources'], 'lead_count': len(snapshot['opportunities']),
                    'ai_state': snapshot['ai_brief']['state'],
                    'company_report': f'data/company/{report["run_id"]}/report.json'})
    history_path.write_text(json.dumps(history, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    render(snapshot)
    print(json.dumps({'run_result': snapshot['run_result'], 'leads': len(snapshot['opportunities']),
                      'sources': snapshot['sources'], 'ai_state': snapshot['ai_brief']['state']}, ensure_ascii=False))
    if snapshot['run_result'] == 'fallido':
        raise SystemExit('All sources failed; see log')


if __name__ == '__main__':
    main()
