# 🏘️ Pueblo IA v1.0 — Operación real, sin ventas ficticias

Un sistema **ejecutable** para rastrear oportunidades públicas, registrar qué fuentes funcionaron, calificarlas, proponer acciones para revisión y presentar la actividad en un pueblo visual. Incluye una demo de producto para ofrecer a negocios.

## Lo que hace de verdad

- Consulta la API gratuita Jobicy (Europa + teletrabajo desde cualquier lugar). Son **ofertas de empleo**, NO cobros ni clientes.
- Consulta el buscador público de comentarios de Hacker News por temas freelance y contract. Son **posibles encargos** que requieren confirmación manual.
- Puntúa oportunidades con reglas transparentes (coincidencia de habilidades), elimina duplicados y conserva la URL original.
- Genera una lista de trabajo para revisar. **No envía solicitudes ni mensajes**.
- Puede llamar a un modelo de IA para resumir hallazgos, **solo si configuras una clave de pago conscientemente**.
- Publica el panel y registra ejecuciones usando GitHub Actions/Pages cada 6 horas (puede haber retrasos).
- Tiene un generador de presupuestos DEMO para mostrar a posibles clientes.
- Un registro de cobros **declarados** permanece en localStorage de tu navegador; no es una conexión bancaria ni prueba independiente.

## Instalación sin pagar alojamiento

1. Crea una cuenta de GitHub o entra en tu cuenta habitual.
2. Crea un repositorio llamado `pueblo-ia`, **público** si quieres usar GitHub Pages con el plan gratuito. **No subas datos bancarios, contraseñas ni información personal**. Mejor créalo sin inicializar README.
3. Sube todos los archivos de este paquete, **incluida la carpeta `.github/workflows`**, a la rama `main`. Puedes usar GitHub Desktop o Git (ver más abajo).
4. Ve a **Settings → Pages → Build and deployment → Source: GitHub Actions**.
5. En **Actions**, ejecuta manualmente `Pueblo IA - Radar y Panel` mediante **Run workflow**, o haz `push` a `main`. La primera ronda consulta las fuentes reales. Si alguna API falla, el error queda registrado.
6. Cuando termine la acción **deploy**, abre la URL que te aparece en GitHub Pages (normalmente `https://TU_USUARIO.github.io/pueblo-ia/`). La URL real la confirma GitHub al desplegar.

### Subir desde Git (si Git ya está instalado en tu PC)

Abre una terminal en esta carpeta descomprimida y ejecuta (sustituyendo `TU_USUARIO`):

```bash
git init
git branch -M main
git add .
git commit -m "Pueblo IA v1"
git remote add origin https://github.com/TU_USUARIO/pueblo-ia.git
git push -u origin main
```

Si Git no está instalado, utiliza GitHub Desktop y publica el repositorio desde esta carpeta. Si creaste el repositorio en GitHub con contenido inicial, tendrás que resolver la sincronización antes de subirlo.

### Opción local (sin despliegue)

Ejecuta esto en la carpeta principal:

```bash
python -m unittest discover -s tests -v
python -m app.run
python -m http.server 8000 --directory site
```

Después abre `http://localhost:8000`. Necesita acceso a Internet para consultar las fuentes. Si no lo tiene, verás los errores en el panel. La web inicial `site/index.html` también se puede abrir directamente, pero no se actualizará automáticamente sin ejecutar la tarea.

### IA generativa (solo si decides pagar uso de API)

Sin claves, el radar y la clasificación ya funcionan. Para habilitar el análisis generativo:

- GitHub → Settings → Secrets and variables → Actions → **Secrets**: `OPENAI_API_KEY`.
- En **Variables**: `OPENAI_MODEL` con un identificador de modelo al que tu cuenta tenga acceso.
- Puedes desactivar la IA eliminando la variable; no hay llamadas API de pago cuando falta clave o modelo.
- Las llamadas de API pueden suponer gasto. **Establece límites de presupuesto en la cuenta proveedora antes de activarla**. No compartas claves en chats ni repositorios.

## Cuidado con GitHub Pages público

Publica únicamente datos que puedan aparecer en una web pública: ofertas vistas en portales y su URL. La información personal del navegador no sale al repositorio. El modelo generativo solo recibe un resumen acotado de las oportunidades públicas.

## Límites reales

- No cobra dinero, no envía candidaturas ni prospecta por DM. Hace investigación y prepara próximas acciones para revisión.
- Buscar ofertas laborales no equivale a crear un negocio ni genera dinero automáticamente.
- GitHub Actions ejecuta rondas programadas, **no es un proceso que permanezca vivo 24 horas**. Las ejecuciones pueden retrasarse y, en repositorios públicos inactivos, suspenderse tras un periodo prolongado.
- El marcado «online» significa **última consulta correcta**, no que haya un agente en marcha en ese instante.
- El sistema no promete beneficios, no verifica el saldo bancario y no tiene permiso para invertir o gastar.
- Las palabras clave son una primera aproximación; pueden aparecer ofertas irrelevantes o antiguas, hay que validar cada una.

## Arquitectura y evidencias

`app/engine.py`: consultas y clasificación. `app/run.py`: orchestration. `app/render.py`: dashboard a partir de datos. `web/template.html`: villa visual. `site/data/latest.json`: foto de última ronda. `site/data/runs.json`: historial de rondas. `site/presupuestador.html`: primera demo comercial. `.github/workflows/pueblo-ia.yml`: trabajo programado + despliegue.

**Política**: no gastar, comprar, contratar, realizar trading real, publicar productos ni enviar mensajes a terceros sin permiso explícito y un flujo de aprobación.

## Mejora v1.1: evitar falsos clientes (14-11-2026)

- El radar de Hacker News solo considera comentarios con expresiones explícitas de demanda (por ejemplo, «we are looking to hire» o «I need help with»).
- Descarta perfiles típicos de profesionales que ofrecen servicios («Location: ... Technologies: ...», «seeking work», «available for hire»).
- Mantiene una etiqueta prudente: **posible comprador sin verificar**, nunca «cliente conseguido».
- Puede reducir drásticamente los hallazgos; **0 oportunidades mejores que 20 falsos clientes**.
- No se han conectado modelos generativos ni automatizado mensajes, compras o cobros.
- Tras copiar este parche al repositorio y hacer commit/push, GitHub Actions regenera automáticamente `site/index.html` y los datos públicos en su siguiente ejecución. No copies ni sobrescribas `site/data`.
