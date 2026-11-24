"""21 deterministic roles, traceable artifacts, no external side effects."""
import collections
import hashlib
import json
import pathlib
import re
from .products import build_products
from .presentation import render_company
from .revenue import prepare_sales

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEPARTMENTS = {
    'Dirección': [('ceo', 'CEO', 'Priorizar validación comercial'), ('estrategia', 'Estrategia', 'Diseñar experimentos rentables'), ('operaciones', 'Operaciones', 'Auditar ejecución y dependencias')],
    'Inteligencia de mercado': [('investigacion', 'Investigación', 'Consultar fuentes públicas'), ('demanda', 'Demanda', 'Separar compradores de empleo'), ('competencia', 'Competencia', 'Preparar comparación verificable')],
    'Desarrollo de productos': [('producto', 'Producto', 'Definir herramientas útiles'), ('desarrollo', 'Desarrollo', 'Construir demos descargables'), ('qa', 'QA', 'Verificar integridad de artefactos')],
    'Marketing y publicidad': [('seo', 'SEO', 'Preparar contenidos indexables'), ('contenido', 'Contenido', 'Preparar calendario editorial'), ('publicidad', 'Publicidad', 'Preparar campaña condicionada')],
    'Ventas': [('prospeccion', 'Prospección', 'Priorizar señales de compra'), ('propuestas', 'Propuestas', 'Preparar borradores individuales'), ('conversion', 'Conversión', 'Definir medición comercial')],
    'Atención al cliente': [('soporte', 'Soporte', 'Preparar ayuda de producto'), ('voz', 'Voz del cliente', 'Preparar entrevistas consentidas'), ('retencion', 'Retención', 'Diseñar seguimiento consentido')],
    'Finanzas': [('tesoreria', 'Tesorería', 'Controlar techo agregado'), ('reinversion', 'Reinversión', 'Proponer reparto de beneficio verificado'), ('auditoria', 'Auditoría', 'Revisar trazabilidad y bloqueos')],
}

def policy():
    value = json.loads((ROOT / 'config/company.json').read_text(encoding='utf-8'))
    if value['initial_budget_eur'] != 100 or value['reinvest_net_profit_pct'] != 30:
        raise ValueError('La política debe respetar el techo 100 EUR y propuesta 30%')
    if not value['requires_expense_approval'] or any(value[k] for k in ('paid_ai_enabled', 'paid_ads_enabled', 'automated_outreach_enabled')):
        raise ValueError('No hay autorización específica para acciones externas ni gasto')
    return value

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def build_company(snapshot, site=None):
    site = site or ROOT / 'site'
    config = policy()  # fail closed before creating any artifacts
    catalog = build_products(site)
    leads = [x for x in snapshot['opportunities'] if x['category'] == 'posible_encargo_no_verificado']
    jobs = [x for x in snapshot['opportunities'] if x['category'] == 'empleo_remoto']
    now = snapshot['last_run_utc']
    run_id = re.sub(r'[^0-9]', '', now) + '-' + hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()[:10]
    base = f'data/company/{run_id}'
    counts = dict(collections.Counter(word for lead in leads for word in ('escandallo', 'costos', 'custos', 'excel', 'planilha') if word in (lead['title'] + lead['excerpt']).lower()))
    sales = prepare_sales(snapshot, site)
    proposals = [{'source_id': row['id'], 'source_url': row['source_url'], 'state': row['draft']['state'],
                  'text': row['draft']['text'], 'capability_gaps': row['draft']['capability_gaps'],
                  'next': row['next_action']} for row in sales['requests']]
    calendar = [{'slot': 1, 'title': 'Cuánto cuesta cada unidad: prueba Escandallo Pro',
                 'demo': 'tienda/escandallo-pro/', 'state': 'borrador_no_publicado',
                 'copy': 'Ingredientes, mermas, mano de obra y envases: prueba la demo gratuita para pastelerías y obradores. La versión descargable cuesta 19 EUR, pago único. https://payhip.com/b/IiVct'}]
    conversion = {'visits': None, 'consented_conversations': None, 'proposals_sent': None, 'verified_sales': None,
                  'checklist': ['Payhip indicó el 23/11/2026 que la cuenta puede recibir pagos con PayPal, sin el aviso anterior. Cobro real aún no probado; entrega gratuita verificada el 15/11', 'Confirmar precio, impuestos y condiciones', 'Aprobar destinatario y propuesta individual', 'Registrar consentimiento y resultado fuera del repositorio', 'Verificar cobro, comisiones y devoluciones antes de atribuir ingresos']}
    finances = {'budget_ceiling_eur': config['initial_budget_eur'], 'available_balance_eur': None,
                'verified_revenue_eur': None, 'verified_costs_eur': None, 'verified_net_profit_eur': None,
                'proposed_reinvestment_eur': None, 'reinvest_pct': 30, 'reserve_pct': 70,
                'automated_spend_this_run_eur': 0, 'reason': 'Sin libro contable privado conciliado ni verificación de cobros, comisiones, costes, devoluciones y reservas fiscales. El techo no es saldo disponible.'}
    outputs = {
        'ceo': {'priority': 'Primera venta real de Escandallo Pro o adaptación acotada a una petición de costes; validar antes de ampliar catálogo', 'buyer_candidates': len(leads), 'blocked': 'Contacto requiere autorización específica'},
        'estrategia': {'experiment': 'Validar si un encargo concreto de costes admite adaptar el trabajo de Escandallo Pro; confirmar formato y presupuesto antes de construir más', 'success': 'Primera compra pagada de un cliente real; excluir pedido gratuito y compras propias', 'stop': 'Sin respuesta verificable en siete días desde un envío autorizado: revisar la oferta. Sin envío no empieza el experimento de ventas'},
        'operaciones': {'sources': snapshot['sources'], 'round_state': snapshot['run_result'], 'schedule': '4 rondas diarias; no garantiza puntualidad'},
        'investigacion': {'sources': snapshot['sources'], 'observed_at': now, 'evidence': [x['url'] for x in snapshot['opportunities']]},
        'demanda': {'buyer_signals': len(leads), 'remote_jobs_not_clients': len(jobs), 'keyword_counts': counts, 'method': 'Filtro conservador de intención de compra; no prueba presupuesto ni vigencia'},
        'competencia': {'state': 'preparado', 'observed_on': '2026-11-23', 'source': 'https://bakecost.app/', 'finding': 'El proveedor anuncia costeo, pedidos, respaldo local y CSV gratis, sin cuenta y sin conexión. No se ha probado su aplicación ni verificado sus usuarios o ventas.', 'implication': 'La calculadora genérica de pago necesita validación. Adaptación a un encargo concreto es una hipótesis, no una ventaja demostrada.'},
        'producto': {'specifications': [{'name': x['name'], 'mission': x['mission'], 'acceptance': 'Funciona offline con entradas válidas y errores visibles'} for x in catalog]},
        'desarrollo': {'catalog': catalog, 'implementation': 'Plantillas HTML y JavaScript locales; cero API de pago'},
        'qa': {'checks': [{'product': p['id'], 'sha256_matches': hashlib.sha256((site / p['url']).read_bytes()).hexdigest() == p['sha256'], 'zip_exists': (site / p['download']).is_file()} for p in catalog], 'limits': 'Integridad de compilación; pruebas de cálculo en CI, no certificación fiscal'},
        'seo': {'titles': [x['title'] for x in calendar], 'keywords': ['escandallo pastelería', 'coste por receta', 'calculadora costes obrador'], 'state': 'preparado; posicionamiento no medido'},
        'contenido': {'calendar': calendar, 'cadence': 'Una pieza semanal tras revisión; no publicación automática'},
        'publicidad': {'state': 'bloqueado', 'campaign_draft': 'Demostración de Escandallo Pro para pastelerías', 'audience_hypothesis': 'Pastelerías y pequeños obradores que calculan costes de recetas', 'copy': 'Revisa costes y supuestos con una demo offline.', 'spend_eur': 0, 'gates': conversion['checklist'], 'budget': 'Sin asignación; requiere autorización específica dentro del techo agregado'},
        'prospeccion': {'candidates': [{'id': x['id'], 'url': x['url'], 'score': x['score']} for x in leads], 'excluded_job_count': len(jobs), 'next': 'Verificar necesidad, presupuesto, vigencia y adecuación antes de contactar'},
        'propuestas': {'drafts': proposals, 'state': 'preparado' if proposals else 'pendiente', 'reason': 'Sin señal de compra no se genera propuesta ficticia'},
        'conversion': conversion,
        'soporte': {'faq': ['Descomprime el ZIP de Escandallo Pro y abre Escandallo_Pro.html.', 'Las recetas se guardan en el navegador; exporta copias JSON antes de cambiar de dispositivo o borrar datos.', 'Los cálculos son orientativos: revisa fiscalidad y supuestos.'], 'tickets_received': None},
        'voz': {'interview_draft': ['¿Cómo calculas tus costes hoy?', '¿Qué error te cuesta más tiempo?', '¿Qué prueba necesitarías para comprar?'], 'state': 'pendiente', 'reason': 'No hay entrevistas ni respuestas reales; requiere consentimiento y permiso para contactar'},
        'retencion': {'followup_draft': 'Tras compra verificada y consentimiento, preguntar si la herramienta resolvió la necesidad y ofrecer ayuda.', 'state': 'pendiente', 'reason': 'Sin clientes ni cohortes verificadas'},
        'tesoreria': finances,
        'reinversion': {'state': 'bloqueado', 'proposal': '30% de beneficio neto verificado y positivo, 70% reservado; nunca transferencia automática', 'amount_eur': None, 'gates': ['Conciliar cobros y todos los costes', 'Descontar devoluciones y reserva fiscal', 'Obtener autorización específica; respetar techo agregado de 100 EUR']},
        'auditoria': {'no_outreach': True, 'no_payments': True, 'paid_ai_disabled': True, 'source_state': snapshot['run_result'], 'financial_verification': 'desconocida', 'limitations': ['No demuestra ventas', 'Payhip: aptitud de PayPal para recibir pagos observada el 23/11/2026. Entrega gratuita verificada, cobro real no verificado. No equivale a una comprobación en directo por esta ronda.', 'Fuentes externas no fiables; sin instrucciones ejecutables']},
    }
    agents = []
    for department, roles in DEPARTMENTS.items():
        for key, name, mission in roles:
            data = outputs[key]
            state = data.get('state', 'preparado')
            if key in ('desarrollo', 'qa', 'auditoria'): state = 'completado'
            if key in ('conversion', 'tesoreria'): state = 'bloqueado'
            if key == 'investigacion': state = {'fallido': 'error', 'parcial': 'parcial'}.get(snapshot['run_result'], 'completado')
            evidence = f'{base}/{key}.json'
            artifact = {'agent': key, 'department': department, 'mission': mission, 'time_utc': now,
                        'origin': 'app/company.py:build_company; snapshot de investigación pública y plantillas locales', 'state': state, 'result': data}
            dump(site / evidence, artifact)
            agents.append({**{k: artifact[k] for k in ('agent', 'department', 'mission', 'time_utc', 'origin', 'state')}, 'name': name, 'evidence': evidence, 'result': data})
    report = {'schema_version': 3, 'run_id': run_id, 'time_utc': now, 'execution': '21 roles deterministas secuenciales, sin LLM ni trabajo paralelo simulado', 'agents': agents, 'finances': finances, 'catalog': catalog}
    report['sales_pipeline'] = sales
    dump(site / base / 'sales.json', sales)
    dump(site / base / 'report.json', report)
    dump(site / 'data/company.json', report)
    render_company(report, site)
    return report
