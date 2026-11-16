"""Read-only v4 presentation of v3 reports. Never creates an execution or alters audit data."""
import datetime as dt
import html
import json
import pathlib
import re
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[1]
# Coordinates, artwork and prose describe the interface, never a live execution.
ZONES = [
    ('direccion', 'Dirección', 'office', 'Orientar y coordinar', '#749e84', 560, 140),
    ('inteligencia', 'Inteligencia de mercado', 'observatory', 'Investigar y validar demanda', '#7ba9ca', 175, 270),
    ('producto', 'Desarrollo de productos', 'factory', 'Diseñar, construir y probar', '#56a997', 450, 380),
    ('marketing', 'Marketing y publicidad', 'studio', 'Preparar la próxima campaña', '#b09bc8', 815, 260),
    ('ventas', 'Ventas', 'store', 'De la señal a la propuesta', '#d5967b', 925, 530),
    ('clientes', 'Atención al cliente', 'support', 'Escuchar, ayudar y aprender', '#d2b86e', 620, 630),
    ('finanzas', 'Finanzas', 'bank', 'Verificar antes de reinvertir', '#86a4ae', 205, 565),
]
STATUS = {
    'completado': ('Completado', 'done'), 'preparado': ('Preparado', 'ready'),
    'pendiente': ('Pendiente', 'pending'), 'bloqueado': ('Bloqueado', 'blocked'),
    'parcial': ('Parcial', 'pending'), 'error': ('Error', 'blocked'),
    'desconocido': ('Sin datos', 'unknown'),
}
ICONS = {
    'village': '<path d="m3 10 5-4 5 4v10H3Z M13 11l4-3 4 3v9h-8 M7 20v-6h3v6 M5 5V2h4v3"/>',
    'office': '<path d="M5 21V6l7-3 7 3v15 M3 21h18 M9 8h1m4 0h1M9 12h1m4 0h1M10 21v-5h4v5"/>',
    'observatory': '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6 M7 10h6m-3-3v6"/>',
    'factory': '<path d="M3 21V10l6 4V9l6 4V3h4l2 18Z M7 17h1m4 0h1m4 0h1"/>',
    'studio': '<path d="m3 10 15-6v16L3 14Z M6 15l2 6h4l-2-5 M21 9v6"/>',
    'store': '<path d="M4 10v11h16V10 M3 10l2-7h14l2 7 M3 10c0 4 4 4 5 0 1 4 4 4 5 0 1 4 4 4 8 0 M9 21v-7h6v7"/>',
    'support': '<path d="M4 12a8 8 0 0 1 16 0v6c0 3-4 3-6 3 M4 12H2v6h4v-6Z M20 12h2v6h-4v-6Z"/>',
    'bank': '<path d="m2 8 10-6 10 6Z M4 11v7m5-7v7m6-7v7m5-7v7 M2 22h20M3 19h18"/>',
    'arrow': '<path d="M4 12h16m-6-6 6 6-6 6"/>',
    'check': '<path d="m5 12 4 4L19 6"/>',
    'lock': '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V6a4 4 0 0 1 8 0v4m-4 5v2"/>',
    'clock': '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
    'download': '<path d="M12 3v12m-5-5 5 5 5-5 M4 17v4h16v-4"/>',
    'file': '<path d="M14 2H5v20h14V7Z M14 2v5h5M8 12h8m-8 4h8"/>',
    'pause': '<path d="M8 5v14M16 5v14"/>',
    'coin': '<circle cx="12" cy="12" r="9"/><path d="M16 7h-4c-5 0-5 10 0 10h4M6 10h8m-8 4h8"/>',
    'code': '<path d="m8 7-5 5 5 5m8-10 5 5-5 5M14 3l-4 18"/>',
}
LABELS = {
    'priority': 'Prioridad', 'buyer_candidates': 'Candidatos de compra', 'blocked': 'Bloqueo',
    'experiment': 'Experimento propuesto', 'success': 'Criterio de éxito', 'stop': 'Criterio de parada',
    'sources': 'Fuentes', 'round_state': 'Estado de la ronda', 'schedule': 'Programación',
    'observed_at': 'Fecha de observación', 'evidence': 'Fuentes de evidencia', 'buyer_signals': 'Señales de compra',
    'remote_jobs_not_clients': 'Empleos, no clientes', 'keyword_counts': 'Coincidencias de palabras',
    'method': 'Método', 'state': 'Estado', 'reason': 'Motivo', 'plan': 'Plan pendiente',
    'specifications': 'Especificaciones', 'name': 'Nombre', 'mission': 'Misión', 'acceptance': 'Aceptación',
    'catalog': 'Catálogo', 'implementation': 'Implementación', 'checks': 'Comprobaciones', 'limits': 'Límites',
    'titles': 'Títulos preparados', 'keywords': 'Palabras clave', 'calendar': 'Calendario editorial',
    'cadence': 'Frecuencia propuesta', 'campaign_draft': 'Borrador de campaña', 'audience_hypothesis': 'Hipótesis de audiencia',
    'copy': 'Texto preparado', 'spend_eur': 'Gasto de campaña EUR', 'gates': 'Condiciones previas', 'budget': 'Presupuesto',
    'candidates': 'Candidatos', 'excluded_job_count': 'Empleos excluidos', 'next': 'Siguiente paso',
    'drafts': 'Borradores', 'visits': 'Visitas', 'consented_conversations': 'Conversaciones consentidas',
    'proposals_sent': 'Propuestas enviadas', 'verified_sales': 'Ventas verificadas', 'checklist': 'Comprobaciones pendientes',
    'faq': 'Ayuda preparada', 'tickets_received': 'Consultas recibidas', 'interview_draft': 'Guion de entrevista',
    'followup_draft': 'Borrador de seguimiento', 'proposal': 'Propuesta', 'amount_eur': 'Importe EUR',
    'no_outreach': 'Sin contactos automáticos', 'no_payments': 'Sin pagos automáticos',
    'paid_ai_disabled': 'IA de pago desactivada', 'source_state': 'Estado de fuentes',
    'financial_verification': 'Verificación financiera', 'limitations': 'Límites de verificación',
    'budget_ceiling_eur': 'Techo agregado EUR', 'available_balance_eur': 'Saldo disponible EUR',
    'verified_revenue_eur': 'Ingresos verificados EUR', 'verified_costs_eur': 'Costes verificados EUR',
    'verified_net_profit_eur': 'Beneficio neto verificado EUR', 'proposed_reinvestment_eur': 'Reinversión propuesta EUR',
    'reinvest_pct': 'Porcentaje propuesto', 'reserve_pct': 'Porcentaje reservado',
    'automated_spend_this_run_eur': 'Gasto automatizado de esta ronda EUR',
}


def esc(value):
    return html.escape(str(value), quote=True)


def icon(name, css='icon'):
    return f'<svg class="{css}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS.get(name, ICONS["file"])}</svg>'


def state_key(raw):
    value = str(raw).lower().split(';')[0].strip()
    return value if value in STATUS else 'desconocido'


def badge(raw):
    label, css = STATUS[state_key(raw)]
    return f'<span class="status {css}"><i></i>{label}</span>'


def local_url(raw, prefix):
    """Only repository-relative file URLs; audit data cannot introduce active URLs."""
    raw = str(raw or '')
    if not re.fullmatch(r'[A-Za-z0-9_./-]+', raw) or raw.startswith('/') or '..' in raw.split('/'):
        return None
    return prefix + raw


def link(raw, label, prefix, css='text-link', download=False):
    url = local_url(raw, prefix)
    if url is None:
        return f'<span>{esc(label)} · enlace no disponible</span>'
    return f'<a class="{css}" href="{esc(url)}"{" download" if download else ""}>{esc(label)}{icon("arrow") if not download else icon("download")}</a>'


def timestamp(value):
    try:
        date = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if date.tzinfo is None:
            return 'Fecha sin zona horaria'
        return date.astimezone(ZoneInfo('Europe/Madrid')).strftime('%d/%m/%Y · %H:%M') + ' Madrid'
    except (ValueError, TypeError):
        return 'Fecha no disponible'


def number(value, money=False):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return '—'
    text = f'{value:,.2f}' if money and value % 1 else f'{value:,g}'
    return text.replace(',', '_').replace('.', ',').replace('_', '.') + (' €' if money else '')


def view_model(report):
    """Derive counts only from recorded fields. None remains unknown, including zero-safe metrics."""
    agents = report.get('agents', [])
    by_id = {a['agent']: a for a in agents}
    def result(key):
        return by_id.get(key, {}).get('result', {})
    departments = []
    for key, name, art, mission, color, x, y in ZONES:
        roles = [a for a in agents if a['department'] == name]
        states = [state_key(a.get('state')) for a in roles]
        aggregate = next((s for s in ('error', 'bloqueado', 'parcial', 'pendiente', 'desconocido', 'preparado') if s in states), 'completado') if roles else 'desconocido'
        departments.append({'id': key, 'name': name, 'art': art, 'mission': mission, 'color': color,
                            'x': x, 'y': y, 'roles': roles, 'state': aggregate,
                            'completed': states.count('completado')})
    catalog = report.get('catalog', [])
    finance = report.get('finances', {})
    return {'departments': departments, 'agents': by_id,
            'products': sum(p.get('state') == 'demo_funcional' for p in catalog),
            'buyers': result('demanda').get('buyer_signals'),
            'sales': result('conversion').get('verified_sales'),
            'spend': finance.get('automated_spend_this_run_eur'),
            'budget': finance.get('budget_ceiling_eur'),
            'reinvestment_pct': finance.get('reinvest_pct'),
            'reinvestment_amount': finance.get('proposed_reinvestment_eur'),
            'calendar': result('contenido').get('calendar', []),
            'proposals': result('propuestas').get('drafts', []),
            'checklist': result('conversion').get('checklist', [])}


def audit_link(agent, prefix, label='Ver evidencia JSON'):
    return link(agent.get('evidence'), label, prefix)


def structured_result(value):
    """Readable audit fallback; strings are always text, never markup or remote instructions."""
    if isinstance(value, dict):
        return '<dl class="result-fields">' + ''.join(f'<div><dt>{esc(LABELS.get(k, k.replace("_", " ")))}</dt><dd>{structured_result(v)}</dd></div>' for k, v in value.items()) + '</dl>'
    if isinstance(value, list):
        return '<ul class="result-list">' + ''.join(f'<li>{structured_result(v)}</li>' for v in value) + '</ul>' if value else '<span class="muted">Sin registros</span>'
    if value is None:
        return '<span class="muted">Desconocido · sin verificar</span>'
    if isinstance(value, bool):
        return 'Sí' if value else 'No'
    return esc(value)


def role_cards(agents, prefix):
    return ''.join(f'''<details class="role-card" id="{esc(a['agent'])}">
<summary><span class="role-avatar">{esc(a['name'][:1])}</span><span><strong>{esc(a['name'])}</strong><small>Rol del sistema</small></span>{badge(a.get('state'))}</summary>
<div class="role-body"><p>{esc(a['mission'])}</p><p class="audit-meta">{icon('clock')}{esc(timestamp(a.get('time_utc')))}</p>
{structured_result(a.get('result', {}))}
{audit_link(a, prefix)}<details class="raw-data"><summary>Datos completos y origen</summary><p>{esc(a.get('origin', 'Origen no disponible'))}</p><pre>{esc(json.dumps(a.get('result', {}), ensure_ascii=False, indent=2))}</pre><small>Estado original: {esc(a.get('state'))}</small></details></div></details>''' for a in agents)


def business_route(vm, prefix, on_map=False):
    steps = [('producto', '01', 'Producto', f'{vm["products"]} demos funcionales', 'Demo disponible'),
             ('marketing', '02', 'Marketing', f'{len(vm["calendar"])} contenidos preparados', 'Borradores, sin difusión'),
             ('ventas', '03', 'Venta', 'Checkout y entrega por validar', 'Sin venta verificada'),
             ('finanzas', '04', 'Finanzas', 'Cobros y costes por conciliar', 'Importe sin verificar')]
    # Labels never promote a sale merely because a demo exists.
    if vm['sales'] is not None:
        steps[2] = ('ventas', '03', 'Venta', f'{number(vm["sales"])} ventas verificadas registradas', 'Según informe de conversión')
    output = []
    for zone, index, name, summary, state in steps:
        href = f'#departamento-{zone}' if on_map else f'{prefix}empresa/#departamento-{zone}'
        output.append(f'<a class="journey-step" href="{href}" {f"data-department={zone}" if on_map else ""}><span class="step-number">{index}</span><div><strong>{name}</strong><p>{esc(summary)}</p><small>{esc(state)}</small></div>{icon("arrow")}</a>')
    return '<div class="business-route">' + ''.join(output) + '</div>'


def product_feature(prefix):
    return f'''<section class="product-feature" id="escandallo-pro"><div class="product-visual" aria-hidden="true"><div class="product-box"><span class="box-brand">Escandallo Pro</span><span class="box-mark">e<span>p</span></span><span class="box-title">ESCANDALLO<br>PRO</span><span class="box-rule"></span><small>COSTE / PRECIO / MARGEN</small></div></div><div class="product-story"><p class="eyebrow">PASTELERÍAS Y PEQUEÑOS OBRADORES</p><h2>Escandallo Pro<span class="dot-accent">.</span></h2><p>Calcula el coste de tus recetas, incorpora gastos y estima un precio con margen.</p><span class="status ready"><i></i>Publicado en Payhip · 19 €</span><p class="product-note">Pago único, sin suscripción. ZIP con aplicación HTML y guía; funciona sin conexión tras descargarlo. Publicación comprobada el 16/11/2026. La prueba gratuita de entrega no representa una venta.</p><div class="button-row">{link('tienda/escandallo-pro/', 'Probar demo de pastelería', prefix, 'button primary')}<a class="button secondary" href="https://payhip.com/b/IiVct" rel="noopener noreferrer">Ver producto · 19 €</a></div><p class="source-note">Demo simplificada, sin registro ni recogida de datos. La disponibilidad de compra se consulta en Payhip.</p></div></section>'''


def kpi_cards(vm):
    items = [
        ('factory', 'Productos activos', number(vm['products']), 'Demos funcionales, no ventas', 'productos'),
        ('observatory', 'Compradores detectados', number(vm['buyers']), 'Señales públicas por validar', 'compradores'),
        ('store', 'Ventas verificadas', number(vm['sales']), 'Sin verificar' if vm['sales'] is None else 'Según informe de conversión', 'ventas'),
        ('coin', 'Gasto automatizado', number(vm['spend'], True), 'Solo en la última ronda', 'gasto'),
        ('bank', 'Presupuesto máximo', number(vm['budget'], True), 'Techo agregado, no saldo', 'presupuesto'),
        ('arrow', 'Reinversión propuesta', number(vm['reinvestment_pct']) + (' %' if vm['reinvestment_pct'] is not None else ''),
         'Importe sin verificar' if vm['reinvestment_amount'] is None else number(vm['reinvestment_amount'], True) + ' · propuesta', 'reinversion'),
    ]
    return '<section class="kpi-grid" aria-label="Indicadores del último informe">' + ''.join(f'<article class="kpi" data-kpi="{key}"><div class="kpi-label">{icon(art)}<h2>{title}</h2></div><strong class="kpi-value">{esc(value)}</strong><small>{esc(note)}</small></article>' for art, title, value, note, key in items) + '</section><p class="metric-note">«Productos activos» cuenta demos funcionales del catálogo. Las señales de compradores no son clientes confirmados. La reinversión propuesta depende del beneficio neto verificado.</p>'


def building_art(art, color):
    # Hand-drawn SVG miniatures, bundled locally; the building is also a normal link.
    extra = {
        'office': '<path d="M-12-67v-48h28v50" fill="#e8e5d5" stroke="#566e60"/><path d="m-20-115 22-12 24 12Z" fill="#3e6860"/><circle cx="2" cy="-96" r="9" fill="#faf5df"/><path d="M2-102v7l5 2" fill="none" stroke="#47695e" stroke-width="2"/>',
        'observatory': '<path d="M-38-64a40 40 0 0 1 80 0Z" fill="#a5cada" stroke="#5d869b"/><path d="m-2-90 15-12 40 16-7 14Z" fill="#335c75"/><circle cx="49" cy="-79" r="8" fill="#d4eff0" stroke="#335c75" stroke-width="4"/>',
        'factory': '<path d="M-56-41v-34l27 14v-27l28 16v-27l39 24v35Z" fill="#85bdac" stroke="#4c8c7b"/><path d="M44-52v-59h15l3 64" fill="#658c83"/><path d="M43-111h19v7H43Z" fill="#365e55"/><rect x="-16" y="-57" width="16" height="10" fill="#d1ecdb"/>',
        'studio': '<rect x="-41" y="-95" width="78" height="36" rx="6" fill="#eee5f3" stroke="#8c75a1"/><path d="m-25-77 43-12v25l-43-7Z" fill="#9b81b4"/><path d="m-18-69 6 12h11l-6-14" fill="#65577a"/><path d="M-35-58v17m66-17v16" stroke="#6c6578" stroke-width="3"/>',
        'store': '<path d="m-62-16 62 26 67-34v16L0 25-62-1Z" fill="#faf0da"/><path d="m-62-16 12 5v15l-12-5Zm24 10 12 5v15l-12-5ZM-14 4 0 10v15l-14-6Zm27-1 13-7v15l-13 7Zm26-13 13-7v15l-13 7Z" fill="#c78169"/><rect x="-25" y="-67" width="47" height="17" rx="3" fill="#f7ebd5"/><text x="-2" y="-54" text-anchor="middle" font-size="10" font-weight="800" fill="#865c48">VENTAS</text>',
        'support': '<path d="M-34-79a34 34 0 0 1 68 0" fill="none" stroke="#816e40" stroke-width="9"/><rect x="-42" y="-83" width="12" height="27" rx="6" fill="#e7d396"/><rect x="30" y="-83" width="12" height="27" rx="6" fill="#e7d396"/><path d="M36-57c0 13-15 17-30 17" fill="none" stroke="#816e40" stroke-width="4"/>',
        'bank': '<path d="m-57-44 58-35 66 28L0-15Z" fill="#cad9d9" stroke="#759298"/><path d="M8-9v45m20-55v45m20-55v45" stroke="#f3f2de" stroke-width="9"/><path d="m-4 42 68-35v9L-4 51Z" fill="#739396"/><circle cx="0" cy="-48" r="12" fill="#4d777a"/><text x="0" y="-43" text-anchor="middle" fill="#f9f3d9" font-size="16" font-weight="700">€</text>',
    }.get(art, '')
    windows = '' if art == 'bank' else '<path d="m13-2 15-7v16l-15 7Zm25-12 15-7v16l-15 7ZM-49-18l14 6V4l-14-6Zm23 10 14 6v16l-14-6Z" fill="#dff1e7" stroke="#6d8c7e" stroke-width="1.3"/>'
    return f'''<ellipse cx="6" cy="65" rx="104" ry="24" fill="#6b8e6e" opacity=".16"/><path d="m-104 29 101-48 108 42L6 78Z" fill="#bdcfb1"/><path d="m-104 23 101-48 108 42L6 72Z" fill="#dce6c7"/><path d="m-64-37 64 27v64l-64-27Z" fill="#b8cabc" stroke="#72978a"/><path d="M0-10 66-42v66L0 54Z" fill="#f2efdb" stroke="#72978a"/><path d="m-74-44 65-34 86 31L0-8Z" fill="{color}" stroke="#537366" stroke-width="1.5"/><path d="m-74-44 74 30 77-33" fill="none" stroke="#f3efdc" stroke-opacity=".45" stroke-width="3"/>{windows}<path d="m-10 29 14-7v30l-14 7Z" fill="#547a6c"/>{extra}'''


def village_map(vm):
    trees = ''.join(f'<g transform="translate({x} {y})"><ellipse cy="13" rx="15" ry="7" fill="#87ab87" opacity=".2"/><path d="M0 0v15" stroke="#899170" stroke-width="4"/><path d="m-14 2 14-31L14 2Z" fill="{color}"/><path d="m-11-11 11-25 11 25Z" fill="#94b89a"/></g>' for x, y, color in [(70, 170, '#719d80'), (280, 115, '#729f85'), (333, 240, '#65977b'), (687, 125, '#83a88b'), (1000, 200, '#729b80'), (1035, 410, '#91af8b'), (77, 495, '#729f85'), (125, 680, '#9ab38f'), (392, 650, '#719d80'), (790, 650, '#94b89a'), (665, 400, '#719d80'), (962, 710, '#729f85')])
    roads = '<path d="M175 315 450 425 815 305 925 575 620 675 205 610 175 315M450 425 560 195M450 425 620 675" fill="none" stroke-linejoin="round" stroke-linecap="round"/>'
    buildings = []
    for d in vm['departments']:
        label, css = STATUS[d['state']]
        dots = ''.join(f'<circle cx="{i*13-13}" cy="85" r="4" class="role-dot {STATUS[state_key(a.get("state"))][1]}"/>' for i, a in enumerate(d['roles']))
        buildings.append(f'''<a href="#departamento-{d['id']}" data-department="{d['id']}" class="building" aria-label="{esc(d['name'])}: {esc(label)}. Abrir {len(d['roles'])} roles y evidencias."><g transform="translate({d['x']} {d['y']}) scale(.9)"><ellipse class="selection-ring" cx="0" cy="35" rx="113" ry="53"/>{building_art(d['art'], d['color'])}<g class="building-label"><rect x="-122" y="96" width="244" height="51" rx="12"/><text x="0" y="117" class="building-name">{esc(d['name'])}</text><text x="0" y="135" class="building-state {css}">{esc(label)} · {len(d['roles'])} roles</text></g>{dots}</g></a>''')
    couriers = ''.join(f'<g class="courier courier-{i}" aria-hidden="true"><ellipse cy="14" rx="11" ry="5" fill="#34584f" opacity=".2"/><path d="M-6 10V0a6 6 0 0 1 12 0v10" fill="{color}"/><circle cy="-6" r="5" fill="#e7c49e"/><path d="M-5-9a5 5 0 0 1 10 0" fill="#284f47"/><rect x="4" y="1" width="7" height="8" rx="1" fill="#f6f0d6"/></g>' for i, color in enumerate(['#456d83', '#7d6893', '#9f7558']))
    return f'''<div class="map-scroll" tabindex="0" role="region" aria-label="Mapa interactivo de siete departamentos. En móvil puedes desplazarlo horizontalmente."><svg class="village-svg" viewBox="0 0 1100 800" role="group" aria-labelledby="map-title map-description"><title id="map-title">El pueblo de los siete departamentos</title><desc id="map-description">Edificios seleccionables conectados por caminos. Las figuras móviles ilustran la ruta prevista entre roles; no indican ejecuciones en directo ni ventas.</desc><defs><pattern id="map-grid" width="40" height="24" patternUnits="userSpaceOnUse"><path d="M0 12 20 0 40 12 20 24Z" fill="none" stroke="#b6cfbb" stroke-width=".6" opacity=".35"/></pattern><marker id="route-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="m1 1 7 4-7 4" fill="none" stroke="#749c8b" stroke-width="1.5"/></marker></defs><rect width="1100" height="800" fill="url(#map-grid)"/><ellipse cx="545" cy="425" rx="505" ry="345" fill="#e6edda" opacity=".75"/><g class="road-outline">{roads}</g><g class="roads">{roads}</g><g class="road-markings">{roads}</g><path d="M250 340 370 388M540 395 730 332M845 373 885 470M800 616 320 630" class="flow-arrows" marker-end="url(#route-arrow)"/>{trees}<g class="plaza" transform="translate(685 478)"><ellipse rx="49" ry="26" fill="#ccdac6"/><ellipse rx="34" ry="17" fill="#b4d6ce" stroke="#f5f3e3" stroke-width="6"/><path d="M0-14v15" stroke="#8fae9e" stroke-width="6"/><ellipse cy="-15" rx="16" ry="7" fill="#edf3df"/></g>{''.join(buildings)}{couriers}<text x="34" y="787" class="map-caption">PUEBLO IA / MAPA DE OPERACIONES</text><text x="1066" y="787" text-anchor="end" class="map-caption">7 ZONAS · ROLES DEL SISTEMA</text></svg></div>'''


def department_panels(vm, prefix):
    output = []
    for d in vm['departments']:
        output.append(f'''<section class="department-panel" id="departamento-{d['id']}" data-panel="{d['id']}" aria-labelledby="title-{d['id']}"><div class="department-heading"><span class="zone-icon" style="--zone:{d['color']}">{icon(d['art'])}</span><div><p class="eyebrow">DEPARTAMENTO / {len(d['roles'])} ROLES</p><h3 id="title-{d['id']}" tabindex="-1">{esc(d['name'])}</h3></div></div><p>{esc(d['mission'])}</p><div class="department-summary">{badge(d['state'])}<small>{d['completed']} de {len(d['roles'])} roles completados</small></div>{role_cards(d['roles'], prefix)}</section>''')
    return '<aside class="inspector" id="inspector"><div class="inspector-top"><span>Dentro del edificio</span><button class="text-button" id="all-roles" type="button" hidden>Ver los 21 roles</button></div>' + ''.join(output) + '</aside>'


def operations(vm, prefix):
    summaries = {
        'investigacion': 'Consulta de fuentes públicas', 'desarrollo': 'Construcción de herramientas digitales',
        'contenido': 'Preparación de contenido editorial', 'prospeccion': 'Revisión de señales de compra',
    }
    rows = []
    for key, title in summaries.items():
        a = vm['agents'].get(key)
        if not a:
            continue
        result = a.get('result', {})
        if key == 'investigacion':
            sources = result.get('sources', [])
            summary = f'{sum(s.get("state") == "ok" for s in sources)} de {len(sources)} fuentes consultadas correctamente.'
        elif key == 'desarrollo':
            summary = f'{len(result.get("catalog", []))} demos registradas en el catálogo de la ronda.'
        elif key == 'contenido':
            summary = f'{len(result.get("calendar", []))} borradores preparados; no se han difundido.'
        else:
            summary = f'{len(result.get("candidates", []))} señales candidatas. Las ofertas de empleo se excluyen de compradores.'
        rows.append(f'<article class="operation"><span class="operation-marker">{icon("file")}</span><div><div class="operation-title"><h3>{title}</h3>{badge(a.get("state"))}</div><p>{esc(summary)}</p><div class="operation-meta"><span>{esc(a["name"])} · {esc(timestamp(a.get("time_utc")))}</span>{audit_link(a, prefix, "Evidencia")}</div></div></article>')
    return '<section class="panel operations"><div class="section-heading"><div><p class="eyebrow">BITÁCORA DE LA ÚLTIMA RONDA</p><h2>Operaciones en marcha</h2></div>' + icon('clock') + '</div><p class="section-note">Resultados registrados, no una ejecución en directo. Cada entrada enlaza con su evidencia.</p>' + ''.join(rows) + '</section>'


def next_steps(vm, prefix):
    tasks = [
        ('inteligencia', 'Revisar las señales de demanda', 'Validar necesidad, presupuesto y vigencia antes de preparar un contacto.', 'Pendiente'),
        ('ventas', 'Comprobar checkout y entrega', 'Verificar el recorrido de Escandallo Pro antes de plantear difusión comercial.', 'Pendiente'),
        ('marketing', 'Revisar campaña y permisos', 'Contenido y propuestas requieren revisión. No hay anuncios de pago activados.', 'Bloqueado'),
        ('finanzas', 'Conciliar cobros y costes', 'Solo entonces se puede calcular el 30% de reinversión propuesto.', 'Bloqueado'),
    ]
    return '<section class="panel next-steps"><div class="section-heading"><div><p class="eyebrow">EL SIGUIENTE TRAMO</p><h2>Próximos pasos</h2></div>' + icon('arrow') + '</div><ol>' + ''.join(f'<li><span class="task-number">{i+1:02}</span><div><a href="{prefix}empresa/#departamento-{zone}">{title}</a><p>{text}</p>{badge(state.lower())}</div></li>' for i, (zone, title, text, state) in enumerate(tasks)) + '</ol><p class="section-note">Acciones propuestas a partir de los límites actuales. No se han ejecutado ni enviado.</p></section>'


def overview(report, vm, prefix):
    shortcuts = ''.join(f'<a href="#departamento-{d["id"]}" data-department="{d["id"]}" class="zone-shortcut">{icon(d["art"])}<span>{esc(d["name"])}</span><i class="state-dot {STATUS[d["state"]][1]}"></i></a>' for d in vm['departments'])
    return kpi_cards(vm) + f'''<section class="village-panel"><div class="map-heading"><div><p class="eyebrow">SIETE DEPARTAMENTOS. UNA MISMA RUTA.</p><h2>El pueblo, a vista de pájaro</h2></div><div class="legend"><span><i class="state-dot done"></i>Completado</span><span><i class="state-dot pending"></i>Pendiente</span><span><i class="state-dot blocked"></i>Bloqueado</span><span><i class="state-dot ready"></i>Preparado</span></div></div><div class="village-layout"><div class="map-column"><p class="map-flow-label"><strong>FLUJO PREVISTO</strong> Investigación <span>→</span> Producto <span>→</span> Marketing <span>→</span> Ventas <span>→</span> Finanzas</p>{village_map(vm)}<div class="map-controls"><p>Movimiento ilustrativo del flujo. No representa actividad en directo.</p><button id="motion-toggle" class="motion-button" type="button" aria-pressed="false" hidden>{icon('pause')}<span>Pausar movimiento</span></button></div><div class="department-shortcuts" aria-label="Seleccionar departamento">{shortcuts}</div></div>{department_panels(vm, prefix)}</div><noscript><p class="section-note">JavaScript desactivado: los edificios enlazan al detalle de cada departamento, visible debajo del mapa.</p></noscript></section><section class="route-section" id="ruta-comercial"><div class="section-heading"><div><p class="eyebrow">RUTA PREVISTA · NO CONVERSIÓN MEDIDA</p><h2>Del producto a una venta real</h2></div><span class="small-tag">Cada tramo exige evidencia</span></div>{business_route(vm, prefix, True)}</section>''' + product_feature(prefix) + '<div class="bottom-grid">' + operations(vm, prefix) + next_steps(vm, prefix) + '</div>'


def marketing_page(report, vm, prefix):
    calendar = ''.join(f'<article class="editorial-card"><div class="card-top"><span class="small-tag">PIEZA {esc(p.get("slot", i+1)):s}</span>{badge("preparado")}</div><h3>{esc(p.get("title", "Sin título"))}</h3><p>{esc(p.get("copy", "Sin texto preparado"))}</p><small>Borrador no publicado</small>{link(p.get("demo"), "Herramienta relacionada", prefix)}</article>' for i, p in enumerate(vm['calendar']))
    proposals = ''.join(f'<article class="proposal-card"><span class="status ready"><i></i>Borrador no enviado</span><h3>Referencia {esc(p.get("source_id"))}</h3><p>{esc(p.get("text"))}</p><small>{esc(p.get("next", "Revisión pendiente"))}</small></article>' for p in vm['proposals']) or '<div class="empty-state">' + icon('store') + '<h3>Aún no hay propuestas individuales</h3><p>No hay señales que hayan dado lugar a un borrador. El sistema espera evidencia de demanda, sin inventar compradores.</p></div>'
    relevant = [a for a in report.get('agents', []) if a['department'] in ('Marketing y publicidad', 'Ventas')]
    campaign = vm['agents'].get('publicidad', {}).get('result', {})
    campaign_agent = vm['agents'].get('publicidad', {})
    return f'''<section class="route-section" id="ruta-comercial">{business_route(vm, prefix)}</section><div class="section-heading"><div><p class="eyebrow">CONTENIDO CONSTRUIDO EN LA ÚLTIMA RONDA</p><h2>Del taller al calendario</h2></div><span class="small-tag">{len(vm['calendar'])} borradores · sin difusión</span></div><div class="editorial-grid">{calendar}</div><div class="bottom-grid"><section class="panel"><p class="eyebrow">PUBLICIDAD</p><h2>Una campaña en preparación</h2>{badge(campaign_agent.get('state', 'desconocido'))}<h3 class="campaign-title">{esc(campaign.get('campaign_draft', 'Sin borrador registrado'))}</h3><p>{esc(campaign.get('copy', ''))}</p><div class="callout">{icon('lock')}<p>{esc(campaign.get('budget', 'Presupuesto sin verificar'))}. Gasto registrado de campaña: <b>{number(campaign.get('spend_eur'), True)}</b>.</p></div>{audit_link(campaign_agent, prefix)}</section><section class="panel"><p class="eyebrow">ANTES DE DIFUNDIR</p><h2>Comprobaciones pendientes</h2><ul class="checklist">{''.join(f'<li>{icon("lock")}<span>{esc(item)}</span></li>' for item in vm['checklist'])}</ul></section></div><section class="proposals"><div class="section-heading"><div><p class="eyebrow">VENTAS CON CONTEXTO</p><h2>Propuestas comerciales</h2></div></div>{proposals}</section><section class="panel audit-section"><p class="eyebrow">TRAZABILIDAD</p><h2>Roles, resultados y evidencias</h2>{role_cards(relevant, prefix)}</section>'''


def shop_page(report, vm, prefix):
    arts = ['factory', 'file', 'bank', 'store']
    products = []
    for i, p in enumerate(report.get('catalog', [])):
        products.append(f'''<article class="catalog-card" id="demo-{esc(p['id'])}"><div class="catalog-art art-{i % 4}">{icon(arts[i % 4], 'product-glyph')}<span>HERRAMIENTA / {i+1:02}</span></div><div class="catalog-body"><span class="small-tag">{esc(p.get('state', 'Sin estado').replace('_', ' '))}</span><h3>{esc(p['name'])}</h3><p>{esc(p.get('mission', ''))}</p><div class="button-row">{link(p.get('url'), 'Abrir demo', prefix, 'button primary')}{link(p.get('download'), 'ZIP offline', prefix, 'button secondary', True)}</div><details class="integrity"><summary>Integridad del archivo HTML</summary><small>SHA-256 del HTML registrado en el informe de la ronda:</small><code>{esc(p.get('sha256', 'Sin hash registrado'))}</code></details></div></article>''')
    return product_feature(prefix) + f'''<section class="route-section" id="ruta-comercial"><div class="section-heading"><div><p class="eyebrow">EL RECORRIDO DEL PRODUCTO</p><h2>Construir. Preparar. Validar.</h2></div></div>{business_route(vm, prefix)}</section><div class="section-heading"><div><p class="eyebrow">SALIDAS DEL TALLER</p><h2>Herramientas que puedes probar</h2></div><span class="small-tag">{vm['products']} demos funcionales</span></div><p class="section-note">Sin registro ni recogida de datos. Descarga el ZIP y abre index.html. Cálculos orientativos: revisa impuestos y supuestos. Su disponibilidad no demuestra compras ni ingresos.</p><section class="catalog-grid" aria-label="Catálogo de demos">{''.join(products)}</section><div class="callout shop-note">{icon('lock')}<p>La compra de Escandallo Pro se realiza en Payhip mediante el enlace de su ficha. Las cuatro demos de este catálogo son herramientas gratuitas independientes. Ningún dato introducido en las demos se incorpora a las métricas auditadas.</p></div>'''


def shell(report, vm, prefix, active, title, subtitle, body):
    nav_items = [('village', 'Vista del pueblo', ''), ('office', 'Departamentos', 'empresa/'), ('studio', 'Marketing', 'marketing/'), ('factory', 'Productos', 'tienda/'), ('observatory', 'Radar de fuentes', 'radar/')]
    nav = ''.join(f'<a href="{prefix}{path or "./"}" class="nav-link {"active" if active == path else ""}" {"aria-current=page" if active == path else ""}>{icon(art)}<span>{name}</span>{"<span class=nav-dot></span>" if active == path else ""}</a>' for art, name, path in nav_items)
    report_link = local_url(f'data/company/{report.get("run_id", "")}/report.json', prefix)
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Pueblo IA v4: un pueblo visual con siete departamentos, roles del sistema y resultados auditados."><meta name="color-scheme" content="light"><title>{esc(title)} · Pueblo IA v4</title><link rel="stylesheet" href="{prefix}assets/pueblo.css"><script src="{prefix}assets/pueblo.js" defer></script></head><body><a class="skip-link" href="#main">Saltar al contenido</a><aside class="sidebar"><a class="brand" href="{prefix}./" aria-label="Pueblo IA, inicio"><span class="brand-icon">{icon('village')}</span><span>PUEBLO<span class="brand-ia">IA<span class="version">V4</span></span></span></a><p class="nav-caption">TU CENTRO DE OPERACIONES</p><nav aria-label="Navegación principal">{nav}</nav><div class="sidebar-project"><span class="project-initials">ep</span><div><small>EN EL ECOSISTEMA</small><a href="{prefix}tienda/#escandallo-pro">Escandallo Pro ↗</a><span>Oferta en Payhip · 19 €</span></div></div><div class="sidebar-bottom"><span class="sidebar-badge">{icon('lock')}Gasto automático desactivado</span><p>Un pueblo pequeño.<br>Decisiones con evidencia.</p><a href="https://github.com/Anguis400/pueblo-ia" target="_blank" rel="noopener noreferrer">{icon('code')}Repositorio y código ↗</a></div></aside><div class="app-main"><header class="topbar"><div class="breadcrumb">Pueblo IA <span>/</span> <strong>{esc(title)}</strong></div><a class="round-indicator" href="{esc(report_link) if report_link else prefix+'data/company.json'}">{icon('clock')}<span>Última ronda<strong>{esc(timestamp(report.get('time_utc')))}</strong></span>{icon('arrow')}</a></header><main id="main"><div class="page-heading"><div><p class="eyebrow">EMPRESA AUTOMATIZADA · RESULTADOS AUDITADOS</p><h1>{esc(title)}<span class="dot-accent">.</span></h1><p>{esc(subtitle)}</p></div><a class="button secondary evidence-button" href="{prefix}data/company.json">{icon('file')}Informe de la ronda</a></div><div class="truth-strip">{icon('code')}<p><strong>{len(report.get('agents', []))} roles del sistema</strong> · Módulos deterministas por rondas, sin 21 LLM en paralelo. El movimiento del mapa es ilustrativo.</p></div>{body}<footer><span>PUEBLO IA <b>V4</b> · Hechos antes que promesas.</span><div><a href="{prefix}data/runs.json">Historial de rondas</a><a href="{prefix}data/company.json">Datos auditados</a></div><small>Estado del informe: {esc(timestamp(report.get('time_utc')))}. No hay medición en directo.</small></footer></main></div></body></html>'''


def render_company(report, site):
    """Rebuild presentation only. Audit JSON, product HTML and ZIPs remain byte-for-byte unchanged."""
    site = pathlib.Path(site)
    assets = site / 'assets'
    assets.mkdir(parents=True, exist_ok=True)
    for name in ('pueblo.css', 'pueblo.js'):
        (assets / name).write_bytes((ROOT / 'web/v4' / name).read_bytes())
    demo = site / 'tienda/escandallo-pro/index.html'
    demo.parent.mkdir(parents=True, exist_ok=True)
    demo.write_bytes((ROOT / 'commerce/payhip/escandallo-demo.html').read_bytes())
    vm = view_model(report)
    pages = [
        ('index.html', '', '', 'Tu empresa, a vista de pueblo', 'Sigue la ruta entre departamentos. Abre un edificio y consulta qué produjo cada rol, con sus evidencias.'),
        ('empresa/index.html', '../', 'empresa/', 'Tu empresa, a vista de pueblo', 'Siete edificios, veintiún roles y una vista compartida de los resultados de la última ronda.'),
        ('marketing/index.html', '../', 'marketing/', 'De la idea a la próxima campaña', 'Contenido, campañas y propuestas preparados para revisión. La difusión comercial requiere autorización.'),
        ('tienda/index.html', '../', 'tienda/', 'El taller de productos', 'Herramientas funcionales, proyectos por validar y una ruta hacia resultados comerciales medibles.'),
    ]
    for path, prefix, active, title, subtitle in pages:
        body = marketing_page(report, vm, prefix) if active == 'marketing/' else shop_page(report, vm, prefix) if active == 'tienda/' else overview(report, vm, prefix)
        target = site / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(shell(report, vm, prefix, active, title, subtitle, body), encoding='utf-8')


if __name__ == '__main__':
    site = ROOT / 'site'
    render_company(json.loads((site / 'data/company.json').read_text(encoding='utf-8')), site)
