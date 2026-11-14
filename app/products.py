"""Offline tools built from trusted source templates; no checkout or telemetry."""
import hashlib
import zipfile

PRODUCTS = [
    ('escandallo', 'Escandallo de servicios', 'Calcular coste y precio objetivo',
     [('coste', 'Coste directo EUR', 0), ('horas', 'Horas', 0), ('tarifa', 'Coste por hora EUR', 0), ('margen', 'Margen objetivo % (menor de 100)', 30)],
     "if(v.margen>=100)throw Error('El margen debe ser menor de 100');const coste=v.coste+v.horas*v.tarifa;return 'Coste: '+money(coste)+' · Precio objetivo sin impuestos: '+money(coste/(1-v.margen/100));"),
    ('presupuesto', 'Presupuesto de proyecto', 'Estimar una propuesta sin enviarla',
     [('horas', 'Horas estimadas', 0), ('tarifa', 'Tarifa EUR por hora', 0), ('extras', 'Extras EUR', 0), ('impuesto', 'Impuesto %', 21)],
     "const base=v.horas*v.tarifa+v.extras;return 'Base: '+money(base)+' · Impuestos: '+money(base*v.impuesto/100)+' · Total: '+money(base*(1+v.impuesto/100));"),
    ('rentabilidad', 'Punto de equilibrio', 'Analizar viabilidad antes de gastar',
     [('fijos', 'Costes fijos EUR', 0), ('variable', 'Coste variable unitario EUR', 0), ('precio', 'Precio sin impuestos EUR', 0)],
     "if(v.precio<=v.variable)throw Error('El precio debe superar el coste variable');return 'Unidades para cubrir costes: '+Math.ceil(v.fijos/(v.precio-v.variable));"),
    ('conversion', 'Embudo comercial', 'Calcular conversión de datos propios',
     [('visitas', 'Visitas medidas', 0), ('consultas', 'Consultas recibidas', 0), ('ventas', 'Ventas verificadas', 0)],
     "if(v.consultas>v.visitas||v.ventas>v.consultas)throw Error('Revisa el orden del embudo');if(!v.visitas)return 'Sin visitas: conversión desconocida';return 'Visita a consulta: '+(100*v.consultas/v.visitas).toFixed(2)+'% · Visita a venta: '+(100*v.ventas/v.visitas).toFixed(2)+'%';"),
]

STYLE = 'body{font:16px/1.6 system-ui;background:#0d1d28;color:#edf5f4;max-width:1100px;margin:auto;padding:24px}a{color:#94eac3}article,details{background:#193440;border:1px solid #42616a;border-radius:14px;padding:20px;margin:16px 0}input,button{font:inherit;padding:10px;margin:8px}label{display:block}button{cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}summary{cursor:pointer}small{color:#b9d0d4}'

def build_products(site):
    folder = site / 'tienda'
    folder.mkdir(parents=True, exist_ok=True)
    catalog = []
    for slug, name, mission, fields, formula in PRODUCTS:
        inputs = ''.join(f'<label>{label}<input name="{key}" type="number" min="0" step="any" value="{default}" required></label>' for key, label, default in fields)
        document = f'''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{name} · Demo</title><style>{STYLE}</style><h1>{name}</h1><p>{mission}. Demo local, sin envío de datos. Importes orientativos; revisa impuestos y supuestos.</p><form>{inputs}<button>Calcular</button></form><output aria-live="polite">Introduce tus datos.</output><p><a href="./">Catálogo</a></p><script>
const money=n=>new Intl.NumberFormat('es-ES',{{style:'currency',currency:'EUR'}}).format(n);
function calculate(v){{{formula}}}
document.querySelector('form').addEventListener('submit',e=>{{e.preventDefault();const v=Object.fromEntries([...new FormData(e.target)].map(([k,x])=>[k,Number(x)]));try{{if(Object.values(v).some(x=>!Number.isFinite(x)||x<0))throw Error('Introduce valores válidos');document.querySelector('output').textContent=calculate(v)}}catch(err){{document.querySelector('output').textContent=err.message}}}});
</script></html>'''
        payload = document.encode('utf-8')
        (folder / f'{slug}.html').write_bytes(payload)
        with zipfile.ZipFile(folder / f'{slug}.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            info = zipfile.ZipInfo('index.html', date_time=(2026, 1, 1, 0, 0, 0))
            archive.writestr(info, payload)
            archive.writestr('LEEME.txt', 'Demo offline. Abre index.html. Sin pagos, servidor ni recogida de datos.')
        catalog.append({'id': slug, 'name': name, 'mission': mission, 'state': 'demo_funcional',
                        'url': f'tienda/{slug}.html', 'download': f'tienda/{slug}.zip',
                        'sha256': hashlib.sha256(payload).hexdigest(), 'sales_verified': None})
    return catalog
