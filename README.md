# 🏘️ Pueblo IA v3 · Empresa operativa auditada

Centro de investigación, fabricación de demos y preparación comercial. Ejecuta **21 roles deterministas secuenciales en 7 departamentos**; no simula 21 LLM ni personas trabajando en paralelo. Una tarea preparada no equivale a una venta ni a una acción comercial ejecutada.

## Uso local

Python 3.12, biblioteca estándar, sin claves ni dependencias Python de pago:

```bash
python -m unittest discover -s tests -v
python -m app.run
python -m http.server 8000 --directory site
```

Abre `http://localhost:8000/empresa/` para consultar el pueblo, los estados, fechas, resultados y evidencias de cada agente. `/` conserva el radar anterior, `/marketing/` presenta borradores y `/tienda/` ofrece cuatro demos HTML y ZIP offline. Node permite ejecutar también las pruebas de las fórmulas JavaScript (disponible en GitHub Actions).

## Trabajo real por departamento

| Departamento | Roles | Resultado verificable |
| --- | --- | --- |
| Dirección | CEO, Estrategia, Operaciones | Prioridades, experimento de adquisición y auditoría de fuentes |
| Inteligencia de mercado | Investigación, Demanda, Competencia | Consultas públicas, separación de empleo/compradores y plan comparativo pendiente de investigación específica |
| Desarrollo de productos | Producto, Desarrollo, QA | Especificaciones, cuatro demos descargables y comprobaciones SHA-256/ZIP |
| Marketing y publicidad | SEO, Contenido, Publicidad | Títulos y palabras clave, calendario con borradores y campaña bloqueada sin inversión |
| Ventas | Prospección, Propuestas, Conversión | Candidatos de compra filtrados, propuestas por señal real y checklist de conversión |
| Atención al cliente | Soporte, Voz del cliente, Retención | FAQ, guion de entrevistas y seguimiento pendiente de clientes y consentimiento |
| Finanzas | Tesorería, Reinversión, Auditoría | Política de capital, propuesta condicionada y controles de trazabilidad |

Jobicy Europa y worldwide proporcionan **empleo remoto**, separado de compradores. HN/Algolia consulta freelance y contract: exige señales explícitas de compra y descarta profesionales buscando trabajo. Los hallazgos no prueban vigencia, presupuesto ni elegibilidad. Sin señal de compra no se fabrica una propuesta. Los siguientes pasos son verificar la conversación original, adaptar una demo, delimitar el alcance y solicitar autorización específica para un destinatario, canal y mensaje. El éxito se mide después con conversación consentida, contrato y cobro conciliado; actualmente esas métricas son desconocidas.

Demos: escandallo de servicios, presupuesto de proyecto, punto de equilibrio y embudo comercial. Funcionan con datos propios, validan entradas y no transmiten información. Son herramientas orientativas, sin certificación contable o fiscal. No son el producto Escandallo Pro conectado en Shopify ni demuestran su checkout o entrega.

## Evidencias e historial

- `site/data/latest.json`: última investigación, incluidas consultas fallidas.
- `site/data/runs.json`: historial acumulativo, sin truncamiento; JSON inválido detiene la ejecución para evitar su destrucción.
- `site/data/snapshots/<ronda>.json`: investigación archivada por ronda nueva.
- `site/data/company.json`: último informe empresarial.
- `site/data/company/<ronda>/`: informe y 21 entregables fechados, con origen, estado y agente.
- `app/engine.py`: fuentes y clasificación; `app/company.py`: roles; `app/products.py`: fábrica de plantillas; `app/run.py`: orquestación; `app/render.py`: radar heredado.

Se conservan los registros heredados de `site/data`. Los nuevos textos públicos omiten correos, teléfonos y patrones comunes de credenciales. Este filtrado es una defensa limitada, no un permiso para incorporar datos privados: no añadir contactos, facturas, identificadores bancarios ni secretos a este repositorio. El contenido remoto se trata como datos no fiables y se escapa al generar HTML. No se ejecutan instrucciones de fuentes externas.

## Capital y permisos

`AGENTS.md` y `config/company.json` fijan **100 EUR de techo agregado**, que no es un saldo disponible. La automatización de esta versión no realiza gastos. Ingresos, costes y beneficio neto verificados permanecen **desconocidos**, al igual que las ventas; cero gasto técnico en una ronda no significa cero costes totales del negocio. Las declaraciones locales del radar no verifican cobros.

Reinversión propuesta: **30% del beneficio neto positivo efectivamente cobrado y verificado**, tras comisiones, costes, devoluciones y reservas fiscales; 70% reservado. No se calcula un importe mientras falte conciliación. No existe conexión bancaria, transferencia, compra, publicidad, registro de cuentas, envío comercial o publicación automática de ofertas. El checkout y la entrega digital de Shopify siguen sin verificar.

La IA de pago está desactivada incluso si existen variables de credenciales. La validación de configuración falla si se intentan activar gasto, publicidad o contacto automático: habilitarlos exige una implementación nueva con autorización específica y controles de coste; cambiar un booleano no los habilita.

## Automatización, revisión y despliegue

`.github/workflows/pueblo-ia.yml` programa **4 rondas/día** (01:17, 07:17, 13:17 y 19:17 UTC; máximo programado inferior a 8/día). Pushes y ejecuciones manuales comparten un límite de 8 rondas por día UTC contado en el historial persistido; al alcanzarlo se conserva el sitio sin nuevas consultas. En PR el historial es una copia aislada y no programa ejecuciones de producción. GitHub puede retrasar o suspender horarios; no hay proceso continuo ni garantía de ejecución. Concurrencia serializa rondas para preservar datos.

Cada ronda ejecuta pruebas antes y después de compilar. Los PR ejecutan `scan` y empaquetan el sitio sin guardar datos en main ni desplegar. Solo main guarda actividad con un commit y, si `scan` pasa, ejecuta `deploy` a GitHub Pages. Configurar Pages para GitHub Actions. Revisar y mezclar el PR es un paso humano: **el despliegue de v3 no se demuestra antes de integrar**. Un fallo de todas las fuentes falla el proceso y evita publicar una ronda como correcta; fallos parciales son visibles.

La investigación inicial del desarrollo del 14/11/2026 consultó cuatro fuentes correctamente: cuatro ofertas remotas, ninguna señal de comprador que pasara los filtros. No hay clientes, ingresos ni beneficios demostrados por esa investigación. Competencia, entrevistas, retención y conversión real siguen pendientes; sus guiones y planes están preparados, sin afirmar que se hayan ejecutado.
