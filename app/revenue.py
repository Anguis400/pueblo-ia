"""Sales preparation tied to observed demand. No sender, payment API or revenue simulation."""
import datetime as dt
import hashlib
import html
import json
import pathlib
import re
from .demand import MAX_AGE_DAYS, folded, project_url, relevant_request
from .engine import plain

ROOT = pathlib.Path(__file__).resolve().parents[1]
UTC = dt.timezone.utc
PRODUCT_URL = 'https://payhip.com/b/IiVct'


def parse_time(value):
    date = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if date.tzinfo is None:
        raise ValueError('A timestamp needs a timezone')
    return date.astimezone(UTC)


def proposal_for(lead):
    """Ask for scope before pricing a deliverable we have not built or agreed to supply."""
    body = folded(lead.get('title', '') + ' ' + lead.get('excerpt', ''))
    spreadsheet = bool(re.search(r'excel|planilh|planilla|spreadsheet|google sheets', body))
    projections = bool(re.search(r'proje[ct]|proyecc|forecast|previs', body))
    gaps = []
    if spreadsheet:
        gaps.append('El encargo pide una hoja de cálculo; el producto actual es HTML local. No son equivalentes.')
    if projections:
        gaps.append('Las proyecciones financieras requieren acordar supuestos y alcance; no se acreditan como función entregada.')
    portuguese = bool(re.search(r'confeitaria|planilha|precifica|custos', body))
    if portuguese:
        text = ('Olá! Vi o pedido de uma ferramenta de custos para a sua confeitaria. '
                'Temos uma demonstração de cálculo por receita. A versão atual é HTML local, não uma planilha Excel. '
                'Antes de propor uma adaptação, prefere Excel ou Google Sheets? Quantas receitas quer incluir '
                'e quais projeções financeiras são necessárias? Trabalhamos com assistência de IA e verificação '
                'dos cálculos. Podemos avaliar o escopo com dados fictícios, sem pedir receitas ou dados de clientes. '
                'Esta consulta não fixa preço nem prazo; qualquer orçamento dependerá de confirmação posterior.')
    else:
        text = ('Hola. He visto vuestra petición de una herramienta de costes. Tenemos una demo de cálculo '
                'por receta; la versión actual es HTML local, no una hoja Excel. Antes de proponer una adaptación, '
                '¿qué formato necesitáis, cuántas recetas y qué previsiones debe incluir? Trabajamos con asistencia '
                'de IA y comprobación de cálculos. Podemos revisar el alcance con datos ficticios, sin pedir recetas '
                'ni datos de clientes. Esta consulta no fija precio ni plazo; cualquier presupuesto se acordará después.')
    return {'language': 'pt' if portuguese else 'es', 'text': text, 'capability_gaps': gaps,
            'price_eur': None, 'delivery_commitment': None,
            'approval_scope': 'Un solo mensaje en la ficha original desde una cuenta profesional autorizada; sin créditos de pago ni suscripciones.',
            'sent_at': None, 'state': 'borrador_no_enviado'}


def build_pipeline(snapshot, previous=None, prepared_at=None):
    prepared = parse_time(prepared_at or dt.datetime.now(UTC).isoformat(timespec='seconds'))
    observed = parse_time(snapshot['last_run_utc'])
    if observed > prepared:
        raise ValueError('Future research cannot qualify a sales request')
    previous = previous or {}
    known = {row['id']: row for row in previous.get('requests', [])}
    requests = []
    rejected = []
    seen = set()
    for lead in snapshot.get('opportunities', []):
        url = project_url(lead.get('url', ''))
        if lead.get('category') != 'posible_encargo_no_verificado' or not url:
            continue
        key = 'workana-' + url.rsplit('/', 1)[1]
        if key in seen:
            continue
        seen.add(key)
        try:
            published = dt.date.fromisoformat(lead['published'])
            age = (prepared.date() - published).days
            live_state = folded(lead.get('project_status_observed', ''))
            eligible = (0 <= age <= MAX_AGE_DAYS and relevant_request(lead.get('title', '') + ' ' + lead.get('excerpt', ''))
                        and live_state in ('evaluating bids', 'evaluando propuestas', 'avaliando propostas', 'open', 'abierto', 'aberto'))
        except (ValueError, TypeError, KeyError):
            eligible = False
        if not eligible:
            rejected.append({'id': key, 'reason': 'Fecha, estado o encaje insuficientes; no preparar contacto.'})
            continue
        draft = proposal_for(lead)
        # A known request is never labelled a newly acquired customer. No delivery is promised.
        requests.append({'id': key, 'source_url': url, 'title': plain(lead['title']),
                         'published': published.isoformat(), 'source_observed_at': lead.get('observed_at', snapshot['last_run_utc']),
                         'tracking_started_at': known.get(key, {}).get('tracking_started_at', prepared.isoformat(timespec='seconds')),
                         'known_to_pipeline': key in known, 'expires_on': (published + dt.timedelta(days=MAX_AGE_DAYS)).isoformat(),
                         'state': 'pendiente_autorizacion_y_acceso', 'budget_eur': None,
                         'next_action': 'Revalidar la ficha y solicitar autorización para esta consulta exacta. Si el canal exige pagar, detenerse.',
                         'draft_sha256': hashlib.sha256(draft['text'].encode()).hexdigest(), 'draft': draft})
    active = {r['id'] for r in requests}
    return {'schema_version': 1, 'prepared_at': prepared.isoformat(timespec='seconds'),
            'source_snapshot_time': snapshot['last_run_utc'], 'research_state': snapshot['run_result'],
            'goal': 'Primer cobro conciliado de un cliente real, excluyendo pedidos gratuitos y compras propias.',
            'existing_offer': {'name': 'Escandallo Pro', 'reference_price_eur': 19, 'url': PRODUCT_URL,
                               'status': 'Publicación documentada previamente; no es comprobación del cobro en esta ronda.'},
            'requests': requests, 'rejected': rejected,
            'no_longer_in_round': sorted(set(known) - active),
            'metrics': {'public_requests_to_validate': len(requests), 'drafts_prepared': len(requests),
                        'messages_sent_by_this_run': 0, 'total_messages_sent': None,
                        'customer_replies': None, 'verified_paid_orders': None, 'verified_net_profit_eur': None},
            'experiment': {'started_at': None, 'review_after_days': 7,
                           'reason': 'El plazo empieza después de un envío autorizado y acreditado; preparar un borrador no lo inicia.'},
            'guardrails': ['Sin envíos, registros de cuenta, compra de créditos ni gasto.',
                           'Revalidar estado, fecha y presupuesto antes de comprometer trabajo.',
                           'Mantener conversación y contratación dentro del canal original.',
                           'No fabricar testimonios, experiencia profesional, respuestas ni cobros.']}


def prepare_sales(snapshot, site, prepared_at=None):
    site = pathlib.Path(site)
    pointer = site / 'data/sales.json'
    try:
        previous = json.loads(pointer.read_text(encoding='utf-8'))
    except FileNotFoundError:
        previous = None
    model = build_pipeline(snapshot, previous, prepared_at)
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(json.dumps(model, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return model


def render_sales(site):
    """A work queue, not a public service offer or an automated sender."""
    site = pathlib.Path(site)
    pointer = site / 'data/sales.json'
    try:
        model = json.loads(pointer.read_text(encoding='utf-8'))
    except FileNotFoundError:
        model = None
    e = lambda x: html.escape(str(x), quote=True)
    cards = []
    for row in model.get('requests', []) if model else []:
        # Evidence files can be untrusted input. Only canonical Workana project links become links.
        source = project_url(row.get('source_url', ''))
        source_link = f'<a href="{e(source)}" rel="noopener noreferrer">Abrir ficha original →</a>' if source else '<span>Enlace inválido; revisar fuente.</span>'
        cards.append(f'''<article class="panel"><span class="status pending"><i></i>Pendiente de autorización y acceso</span><h2>{e(row['title'])}</h2><p>Publicado: {e(row['published'])}. Observado por la fuente: {e(row['source_observed_at'])}. El filtro de antigüedad vence: {e(row['expires_on'])}.</p><ul>{''.join('<li>'+e(x)+'</li>' for x in row['draft']['capability_gaps'])}</ul><h3>Consulta preparada · no enviada</h3><blockquote>{e(row['draft']['text'])}</blockquote><p>{e(row['next_action'])}</p><p>{source_link}</p><small style="overflow-wrap:anywhere">Presupuesto del cliente, precio y plazo: sin acordar. SHA-256 del borrador: {e(row['draft_sha256'])}</small></article>''')
    evidence_link = ' · <a href="../data/sales.json">Evidencia de preparación</a>' if model else ''
    date = f'<p>Preparación: {e(model["prepared_at"])}. Investigación de origen: {e(model["source_snapshot_time"])}.</p>' if model else ''
    empty = '<section class="panel"><h2>Sin consultas comerciales preparadas</h2><p>No se fabrican compradores. Revisa el estado de las fuentes y los encargos recientes antes de iniciar contacto.</p></section>'
    content = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>Primera venta · Pueblo IA</title><link rel="stylesheet" href="../assets/pueblo.css"></head><body><main style="max-width:1000px;padding:32px 20px;margin:auto"><nav><a href="../">Pueblo</a> · <a href="../marketing/">Marketing</a> · <a href="../tienda/">Producto</a>{evidence_link}</nav><div class="page-heading"><div><p class="eyebrow">OPERACIONES COMERCIALES</p><h1>La próxima conversación, con contexto.</h1><p>Objetivo: primer cobro de un cliente real. Esta cola prepara trabajo comercial; no envía mensajes ni demuestra ingresos.</p></div></div>{date}<div class="truth-strip"><p>Ventas y beneficio neto verificados: desconocidos. Cero mensajes enviados por este módulo. No se cuenta un borrador como contacto ni un pedido de prueba como venta.</p></div>{''.join(cards) or empty}<section class="panel"><h2>De consulta a ingreso verificable</h2><ol><li>Autorizar texto, destinatario y canal; disponer de cuenta profesional, sin pagar.</li><li>Obtener respuesta y confirmar formato, alcance y presupuesto.</li><li>Acordar propuesta y condiciones antes de comprometer una entrega.</li><li>Entregar y verificar la aceptación.</li><li>Conciliar el pago de cliente, comisiones, gastos, devoluciones y reserva fiscal en registros privados.</li></ol><p>La revisión de siete días empieza con el envío real acreditado. Reinversión propuesta: 30% del beneficio neto verificado, sin transferencias automáticas.</p></section></main></body></html>'''
    target = site / 'ventas/index.html'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')


if __name__ == '__main__':
    site = ROOT / 'site'
    snapshot = json.loads((site / 'data/latest.json').read_text(encoding='utf-8'))
    model = prepare_sales(snapshot, site)
    render_sales(site)
    print(json.dumps({'drafts': len(model['requests']), 'sent_by_this_run': 0, 'source_time': model['source_snapshot_time']}))
