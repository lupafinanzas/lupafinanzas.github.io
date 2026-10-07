"""Genera una ficha estática por tienda (tienda/<slug>/index.html), el índice tienda/index.html y añade las URLs al sitemap.

Uso: python build_tiendas.py   (desde web/, después de actualizar cashback.json y descuentos.json; antes del commit)
Una ficha por cada tienda con datos suficientes: 2 o más plataformas con cashback, o descuentos vigentes en descuentos.json.
Todo el contenido sale de los datos leídos (con su fecha): ninguna cifra escrita a mano. Pensado para posicionar búsquedas del tipo
«cashback <tienda>» o «código descuento <tienda>» y para que los buscadores con IA puedan citar datos concretos y fechados.
"""
import datetime
import html
import json
import pathlib
import re
import unicodedata

BASE = pathlib.Path(__file__).parent
SITIO = "https://lupafinanzas.github.io"
esc = html.escape
data = json.loads((BASE / "cashback.json").read_text(encoding="utf-8"))
descuentos = json.loads((BASE / "descuentos.json").read_text(encoding="utf-8")).get("descuentos", [])
hoy = datetime.date.today()
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if not unicodedata.combining(c)))


def pc(n):
    return f"{n:g}".replace(".", ",") + " %"


def eur(n):
    return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def fecha(iso):
    a, m, d = iso.split("-")
    return f"{int(d)} de {MESES[int(m) - 1]} de {a}"


def gana(f, imp=50):
    v = imp * f["pct"] / 100
    return min(v, f["tope"]) if f.get("tope") is not None else v


def etiquetas(f):
    e = []
    if f.get("hasta_pct"):
        e.append("máximo anunciado («hasta»)")
    if f["tipo"] == "aumentado":
        e.append(f"subida temporal (habitual {pc(f['habitual_pct'])})" + (f", hasta el {fecha(f['fin'])}" if f.get("fin") else ""))
    if f["tipo"] == "bienvenida" or f.get("solo_clientes_nuevos"):
        e.append("solo clientes nuevos")
    if f.get("primera_compra"):
        e.append("solo la primera compra")
    if f["tipo"] == "categoria":
        e.append("depende de la categoría")
    if f.get("tope") is not None:
        e.append(f"tope {eur(f['tope'])}")
    if f.get("plazo_dias"):
        e.append(f"se cobra en {f['plazo_dias'][0]}–{f['plazo_dias'][1]} días")
    return "; ".join(e) if e else "tarifa habitual"


dto_por_nombre = {}
for d in descuentos:
    dto_por_nombre.setdefault(norm(d["tienda"]), []).append(d)

paginas = []
for t in data["tiendas"]:
    plats = {f["plataforma"] for f in t["filas"]}
    dtos = dto_por_nombre.get(norm(t["nombre"]), [])
    if len(plats) >= 2 or dtos:
        paginas.append((t, sorted(t["filas"], key=lambda f: -gana(f)), dtos))

IGRAAL_CAJA = '<div class="caja"><b>Publicidad.</b> ¿Todavía no tienes iGraal? Si te registras con <a href="{rel}ir/igraal/" rel="noopener sponsored nofollow">mi invitación</a> recibes un bono de 10 € con tu primer pedido de al menos 12,40 € (en 90 días). Yo recibo una recompensa si lo haces. Las condiciones completas están en la web de iGraal.</div>'

CSS = """<style>
.art{max-width:760px;margin:0 auto;padding:24px 16px 8px}
.art h1{font-size:clamp(1.8rem,6vw,2.5rem);margin:6px 0 12px}
.art h2{font-size:1.35rem;margin:28px 0 8px}
.art p,.art li{margin:10px 0}
.tabla{overflow-x:auto;margin:14px 0;border:1px solid var(--line);border-radius:16px;background:var(--card)}
.tabla table{width:100%;border-collapse:collapse;font-size:.92rem}
.tabla th,.tabla td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}
.tabla tr:last-child td{border-bottom:0}
.caja{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 16px;margin:18px 0}
.art details{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 16px;margin:10px 0}
.art summary{cursor:pointer;font-weight:800}
.lista{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:8px;margin:14px 0}
.lista a{display:block;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 12px;text-decoration:none;font-size:.92rem}
</style>"""

MENU = ('<a href="{rel}index.html">Inicio</a><a href="{rel}promociones.html">Promociones</a><a href="{rel}cashback.html">Cashback</a>'
        '<a href="{rel}descuentos.html">Descuentos</a><a href="{rel}comparador.html">Comparador</a><a href="{rel}blog/">Blog</a>'
        '<a href="{rel}como-lo-hacemos.html">Cómo lo hacemos</a>')


def pagina(ruta, titulo, desc, cuerpo, jsonld, rel):
    canon = f"{SITIO}/{ruta}"
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(titulo)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canon}">
<meta property="og:title" content="{esc(titulo)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="https://lupafinanzas.github.io/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta property="og:locale" content="es_ES">
<meta name="theme-color" content="#0b2e25">
<link rel="icon" href="{rel}logo.jpg">
<link rel="stylesheet" href="{rel}fuentes.css">
<link rel="stylesheet" href="{rel}estilo.css">
{CSS}
<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>
</head>
<body>
<header class="top"><div class="wrap">
  <a class="marca" href="{rel}index.html"><img src="{rel}logo.jpg" alt=""><span>Lupa Financiera</span></a>
  <nav class="menu" aria-label="Principal">
    {MENU.format(rel=rel)}
  </nav>
  <a class="x" href="https://x.com/LupaFinanzas">@LupaFinanzas</a>
</div></header>
<main class="wrap">
{cuerpo}
<footer class="pie"><p><a href="{rel}aviso-legal.html">Aviso legal</a> · <a href="{rel}privacidad.html">Política de privacidad</a> · <a href="{rel}cookies.html">Política de cookies</a></p><p>Datos orientativos leídos de fuentes públicas con su fecha; los porcentajes y las condiciones cambian a diario. No es asesoría financiera.</p></footer>
</main>
</body>
</html>
"""



_hp = BASE / "datos" / "historial.json"
HIST = json.loads(_hp.read_text(encoding="utf-8")) if _hp.exists() else {"desde": hoy.isoformat(), "series": {}}


def chispa(puntos):
    """Gráfica mínima (SVG) de una serie [[fecha, pct], ...] con eje de tiempo real."""
    ds = [datetime.date.fromisoformat(f) for f, _ in puntos]
    vs = [v for _, v in puntos]
    t0, t1 = ds[0], ds[-1]
    span = max((t1 - t0).days, 1)
    lo, hi = min(vs), max(vs)
    rango = (hi - lo) or 1
    pts = " ".join(f"{4 + 152 * ((d - t0).days / span):.1f},{30 - 24 * ((v - lo) / rango):.1f}" for d, v in zip(ds, vs))
    return (f'<svg viewBox="0 0 160 36" width="160" height="36" role="img" aria-label="Evolución del cashback entre {fecha(puntos[0][0])} y {fecha(puntos[-1][0])}">'
            f'<polyline points="{pts}" fill="none" stroke="#0f7a58" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/></svg>')


def historia(slug, nombre):
    series = [(k.split("|"), v) for k, v in HIST["series"].items() if k.startswith(slug + "|")]
    con_cambios = [(k, v) for k, v in series if len(v) >= 2]
    desde = fecha(HIST["desde"])
    if not con_cambios:
        return (f'<h2>Evolución del cashback en {esc(nombre)}</h2><p>Guardamos la tarifa de cada plataforma todos los días desde el {desde}. '
                f'Hasta ahora no ha cambiado ninguna en {esc(nombre)}; cuando cambie, aparecerá aquí con su gráfica.</p>')
    filas = []
    for k, v in sorted(con_cambios, key=lambda x: -abs(x[1][-1][1] - x[1][0][1])):
        plat = k[1] + (f" ({k[2]})" if k[2] else "")
        pasos = " → ".join(f"{pc(p)} ({fecha(f)})" for f, p in v[-6:])
        grafica = chispa(v) if len(v) >= 3 else ""
        filas.append(f"<tr><td>{esc(plat)}</td><td>{esc(pasos)}</td><td>{grafica}</td></tr>")
    return (f'<h2>Evolución del cashback en {esc(nombre)}</h2><div class="tabla"><table><thead><tr><th>Plataforma</th><th>Cambios de tarifa</th><th></th></tr></thead><tbody>'
            + "".join(filas) + f'</tbody></table></div><p class="mini">Histórico propio guardado desde el {desde}: solo anotamos un punto cuando la tarifa cambia.</p>')

urls = []
for t, filas, dtos in paginas:
    n = t["nombre"]
    rel = "../../"
    es_nuevo = lambda f: f["tipo"] == "bienvenida" or f.get("solo_clientes_nuevos") or f.get("primera_compra")
    generales = [f for f in filas if not es_nuevo(f)]
    exactas_g = [f for f in generales if not f.get("hasta_pct")]
    mejor = (exactas_g or generales or filas)[0]  # el titular usa la mejor cifra exacta para cualquier cliente
    mejor_hasta = next((f for f in generales if f.get("hasta_pct") and gana(f) > gana(mejor)), None)
    mejor_nuevos = filas[0] if es_nuevo(filas[0]) and filas[0] is not mejor else None
    exactas = [f for f in filas if not f.get("hasta_pct") and f["tipo"] != "bienvenida" and not f.get("solo_clientes_nuevos") and not f.get("primera_compra")]
    habit = max((f for f in exactas if f["tipo"] != "aumentado"), key=lambda f: (f.get("habitual_pct") or 0), default=None)
    plats = sorted({f["plataforma"] for f in filas})
    leido = max(f["leido"] for f in filas)
    vigentes = [d for d in dtos if not d.get("caduca") or d["caduca"] >= hoy.isoformat()]
    codigos = [d for d in vigentes if d["tipo"] == "codigo"]

    # párrafo introductorio con datos
    intro = (f"A {fecha(leido)}, Lupa Financiera compara {len(plats)} plataforma{'s' if len(plats) != 1 else ''} de cashback para {esc(n)}: {esc(', '.join(plats))}. "
             f"Con una compra de 50 €, la que más devuelve es <b>{esc(mejor['plataforma'])}</b>, con {eur(gana(mejor))} ({'hasta ' if mejor.get('hasta_pct') else ''}{pc(mejor['pct'])}). ")
    if mejor_hasta:
        intro += f"{esc(mejor_hasta['plataforma'])} anuncia un máximo más alto («hasta {pc(mejor_hasta['pct'])}»), pero el porcentaje que recibes depende de la categoría o del tipo de compra. "
    if mejor_nuevos:
        intro += f"Para clientes nuevos o en la primera compra hay una oferta más alta: {esc(mejor_nuevos['plataforma'])} con {eur(gana(mejor_nuevos))} ({'hasta ' if mejor_nuevos.get('hasta_pct') else ''}{pc(mejor_nuevos['pct'])}), con las condiciones que indica la tabla. "
    if habit and habit is not mejor:
        intro += f"Sin subidas ni ofertas para clientes nuevos, la tarifa más alta es la de {esc(habit['plataforma'])}: {pc(habit.get('habitual_pct') or habit['pct'])}. "
    if vigentes:
        intro += f"Además hay {len(vigentes)} descuento{'s' if len(vigentes) != 1 else ''} con fecha vigente" + (f", {len(codigos)} de ellos con código" if codigos else "") + "."
    else:
        intro += "Ahora mismo no tenemos descuentos con fecha vigente para esta tienda."

    # tabla de plataformas
    filas_html = []
    for f in filas:
        var = f" ({esc(f['variante'])})" if f.get("variante") else ""
        filas_html.append(f'<tr><td><a href="{esc(f["fuente"])}" rel="noopener nofollow">{esc(f["plataforma"])}</a>{var}</td>'
                          f'<td><b>{"hasta " if f.get("hasta_pct") else ""}{pc(f["pct"])}</b></td><td>{eur(gana(f))}</td><td>{esc(etiquetas(f))}</td><td>{fecha(f["leido"])}</td></tr>')
    tabla = ('<div class="tabla"><table><thead><tr><th>Plataforma</th><th>Cashback</th><th>Con 50 €</th><th>Condiciones</th><th>Leído</th></tr></thead><tbody>'
             + "".join(filas_html) + "</tbody></table></div>")

    # descuentos
    bloque_dto = ""
    if vigentes:
        fd = []
        for d in vigentes[:12]:
            cod = f"<b>{esc(d['codigo'])}</b>" if d.get("codigo") else "—"
            ver = d.get("verificacion")
            estado = ("verificado en la tienda el " + fecha(ver["fecha"])) if ver and ver["estado"] == "verificado" else "visto en la fuente, sin probar en la tienda"
            fd.append(f"<tr><td>{esc(d['valor'] or '—')}</td><td>{esc(d['titulo'])}</td><td>{cod}</td><td>{fecha(d['caduca']) if d.get('caduca') else 'sin fecha de fin'}</td><td>{estado}</td></tr>")
        bloque_dto = ('<h2>Descuentos y códigos vigentes</h2><div class="tabla"><table><thead><tr><th>Descuento</th><th>Oferta</th><th>Código</th><th>Hasta</th><th>Estado</th></tr></thead><tbody>'
                      + "".join(fd) + "</tbody></table></div><p class=\"mini\">Fuente: <a href=\"" + esc(vigentes[0]["fuente"]) + "\" rel=\"noopener nofollow\">Widilo</a>. Los códigos pueden haber caducado o no ser válidos para tu pedido: se muestran con la fecha en que los leímos.</p>")

    # preguntas frecuentes (todas con datos propios)
    faq = [
        (f"¿Qué plataforma da más cashback en {n}?",
         f"A {fecha(leido)}, con una compra de 50 €, la que más devuelve en {n} es {mejor['plataforma']}: {eur(gana(mejor))} ({'hasta ' if mejor.get('hasta_pct') else ''}{pc(mejor['pct'])})."
         + (f" Sin subidas temporales ni ofertas para clientes nuevos, la tarifa más alta es la de {habit['plataforma']}." if habit and habit is not mejor else "")
         + (f" Para clientes nuevos o en la primera compra, {mejor_nuevos['plataforma']} ofrece {eur(gana(mejor_nuevos))} con condiciones." if mejor_nuevos else "")),
        (f"¿Se puede sumar un cupón y el cashback en {n}?",
         (f"Hay {len(vigentes)} descuento(s) con fecha vigente para {n}. Las plataformas suelen marcar las ofertas que se suman al cashback, pero conviene comprobar la condición antes de pagar." if vigentes
          else f"Ahora mismo no tenemos descuentos con fecha vigente para {n}. En general, algunos cupones desactivan el cashback: comprueba la condición de la plataforma antes de pagar.")),
        (f"¿Cómo sé si el porcentaje de cashback de {n} es el habitual?",
         "Cada fila indica si es la tarifa habitual, una subida temporal (con la habitual al lado), un máximo anunciado («hasta») o una oferta solo para clientes nuevos. Las subidas temporales vuelven a su tarifa habitual cuando acaban."),
    ]
    faq_html = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faq)

    hist_html = historia(t["slug"], n)
    cuerpo = (f'<article class="art"><nav class="mini" aria-label="Migas de pan"><a href="{rel}index.html">Inicio</a> › <a href="{rel}tienda/">Tiendas</a> › {esc(n)}</nav>'
              f'<h1>Cashback y descuentos en {esc(n)}</h1><p class="sub">{intro}</p>'
              f'<h2>Cashback en {esc(n)} por plataforma</h2>{tabla}'
              f'<p class="mini">Cálculo orientativo con 50 € y sin IVA ni envío. Cada cifra se lee en la ficha pública de la plataforma, con doble comprobación. Datos leídos el {fecha(leido)}.</p>'
              f'{hist_html}{bloque_dto}'
              + (IGRAAL_CAJA.format(rel=rel) if 'iGraal' in plats else '') +
              f''
              f'<h2>Preguntas frecuentes sobre {esc(n)}</h2>{faq_html}'
              f'<div class="caja"><b>Compáralo con tu importe.</b> <a href="{rel}comparador.html#{esc(t["slug"])}">Abre el comparador</a> y cambia la cantidad para ver los euros que recibirías en cada plataforma.</div>'
              f'<p class="mini"><a href="{rel}blog/">Guías de cashback</a> · <a href="{rel}descuentos.html">Todos los descuentos</a> · <a href="{rel}como-lo-hacemos.html">Cómo comprobamos los datos</a></p></article>')

    titulo = f"Cashback en {n}: qué plataforma devuelve más"
    if len(titulo) > 62:
        titulo = f"Cashback en {n}: comparativa"
    desc = (f"{n}: {eur(gana(mejor))} de cashback con 50 € en {mejor['plataforma']} ({'hasta ' if mejor.get('hasta_pct') else ''}{pc(mejor['pct'])}); "
            f"comparamos {len(plats)} plataforma{'s' if len(plats) != 1 else ''}" + (f" y {len(vigentes)} descuentos vigentes" if vigentes else "") + f". Datos del {fecha(leido)}.")[:158]
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Inicio", "item": SITIO + "/"},
            {"@type": "ListItem", "position": 2, "name": "Tiendas", "item": SITIO + "/tienda/"},
            {"@type": "ListItem", "position": 3, "name": n, "item": f"{SITIO}/tienda/{t['slug']}/"}]},
        {"@type": "WebPage", "name": titulo, "description": desc, "inLanguage": "es", "dateModified": leido,
         "isPartOf": {"@type": "WebSite", "name": "Lupa Financiera", "url": SITIO + "/"}},
        {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}]}
    out = BASE / "tienda" / t["slug"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(pagina(f"tienda/{t['slug']}/", titulo, desc, cuerpo, jsonld, rel), encoding="utf-8")
    urls.append((f"{SITIO}/tienda/{t['slug']}/", leido))

# índice de tiendas
enlaces = "".join(f'<a href="{t["slug"]}/">{esc(t["nombre"])}</a>' for t, _, _ in sorted(paginas, key=lambda x: x[0]["nombre"].lower()))
cuerpo = (f'<article class="art"><h1>Cashback y descuentos por tienda</h1><p class="sub">{len(paginas)} tiendas con ficha propia: qué plataforma devuelve más, '
          f'con qué condiciones y qué descuentos vigentes hay. Datos leídos de fuentes públicas con su fecha.</p><div class="lista">{enlaces}</div></article>')
jsonld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Cashback y descuentos por tienda", "inLanguage": "es", "url": SITIO + "/tienda/"}
(BASE / "tienda").mkdir(exist_ok=True)
(BASE / "tienda" / "index.html").write_text(pagina("tienda/", "Cashback y descuentos por tienda · Lupa Financiera",
    f"{len(paginas)} tiendas con cashback comparado entre plataformas y descuentos vigentes, con fecha de lectura y fuente.", cuerpo, jsonld, "../"), encoding="utf-8")
urls.append((SITIO + "/tienda/", hoy.isoformat()))

# sitemap: base + blog (build_blog.py lo genera) + tiendas
mapa = BASE / "sitemap.xml"
s = mapa.read_text(encoding="utf-8")
s = re.sub(r"<url><loc>[^<]*/tienda/[^<]*</loc>(<lastmod>[^<]*</lastmod>)?</url>\n?", "", s)
extra = "".join(f"<url><loc>{u}</loc><lastmod>{lm}</lastmod></url>\n" for u, lm in urls)
s = s.replace("</urlset>", extra + "</urlset>")
mapa.write_text(s, encoding="utf-8")
print(f"{len(paginas)} fichas de tienda + índice; {len(urls)} URLs añadidas al sitemap")
