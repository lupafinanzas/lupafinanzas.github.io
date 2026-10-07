"""Genera el blog (blog/index.html, blog/<slug>/index.html) y sitemap.xml (robots.txt se mantiene a mano).

Uso: python build_blog.py   (desde web/, después de actualizar cashback.json y antes del commit)
Los artículos viven en blog_src/articulos.json. Los marcados con "tabla" llevan una tabla generada
con los datos reales de cashback.json (con su fecha de lectura): nada de cifras escritas a mano.
Sin datos personales: el blog no los necesita; el aviso legal es aparte (legal_borradores/).
"""
import html
import json
import pathlib

BASE = pathlib.Path(__file__).parent
SITIO = "https://lupafinanzas.github.io"
data = json.loads((BASE / "cashback.json").read_text(encoding="utf-8"))
arts = json.loads((BASE / "blog_src" / "articulos.json").read_text(encoding="utf-8"))
tiendas = {t["slug"]: t for t in data["tiendas"]}
esc = html.escape


def pc(n):
    return f"{n:g}".replace(".", ",") + " %"


def fecha(iso):
    a, m, d = iso.split("-")
    return f"{d}/{m}/{a}"


def tabla(slugs):
    filas = []
    for s in slugs:
        t = tiendas.get(s)
        f = next((x for x in t["filas"] if x["plataforma"] == "mycashbacks"), None) if t else None
        if f:
            filas.append((f["pct"], t["nombre"], f["hasta_pct"], f["leido"], f["fuente"]))
    filas.sort(reverse=True)
    if not filas:
        return ""
    leido = max(f[3] for f in filas)
    out = ['<div class="tabla"><table><thead><tr><th>Tienda</th><th>Cashback en mycashbacks</th></tr></thead><tbody>']
    for pct, nombre, hasta, _, fuente in filas:
        out.append(f'<tr><td><a href="{esc(fuente)}" rel="noopener nofollow">{esc(nombre)}</a></td><td><b>{"hasta " if hasta else ""}{pc(pct)}</b></td></tr>')
    out.append("</tbody></table></div>")
    out.append(f'<p class="mini">Datos leídos el {fecha(leido)} en las fichas públicas de mycashbacks, con doble comprobación (título y bloque de la ficha). Los porcentajes cambian a diario: para ver el de hoy y compararlo con otras plataformas, usa el <a href="../../comparador.html">comparador</a>.</p>')
    return "\n".join(out)


IGRAAL_CAJA = '<div class="caja"><b>Publicidad.</b> ¿Todavía no tienes iGraal? Si te registras con <a href="{rel}ir/igraal/" rel="noopener sponsored nofollow">mi invitación</a> recibes un bono de 10 € con tu primer pedido de al menos 12,40 € (en 90 días). Yo recibo una recompensa si lo haces. Las condiciones completas están en la web de iGraal.</div>'

CSS = """<style>
.art{max-width:720px;margin:0 auto;padding:24px 16px 8px}
.art h1{font-size:clamp(1.9rem,6vw,2.7rem);margin:6px 0 12px}
.art h2{font-size:1.45rem;margin:30px 0 8px}
.art p,.art li{margin:10px 0}
.art ul{padding-left:20px}
.tabla{overflow-x:auto;margin:14px 0;border:1px solid var(--line);border-radius:16px;background:var(--card)}
.tabla table{width:100%;border-collapse:collapse}
.tabla th,.tabla td{text-align:left;padding:10px 14px;border-bottom:1px solid var(--line)}
.tabla tr:last-child td{border-bottom:0}
.lista{display:grid;gap:14px;margin:20px 0}
.lista a.card{display:block;padding:18px;text-decoration:none}
.lista h2{font-size:1.25rem;margin:4px 0 6px}
.caja{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 16px;margin:18px 0}
.caja ul{margin:6px 0 0}
.art details{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 16px;margin:10px 0}
.art summary{cursor:pointer;font-weight:800}
</style>"""


def pagina(ruta, titulo, desc, cuerpo, jsonld=""):
    prof = ruta.count("/")
    rel = "../" * prof
    canon = f"{SITIO}/{ruta}"
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(titulo)} · Lupa Financiera</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canon}">
<meta property="og:title" content="{esc(titulo)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="https://lupafinanzas.github.io/og.png">
<meta property="og:locale" content="es_ES">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0b2e25">
<link rel="icon" href="{rel}logo.jpg">
<link rel="stylesheet" href="{rel}fuentes.css">
<link rel="stylesheet" href="{rel}estilo.css">
{CSS}
{jsonld}
</head>
<body>
<header class="top"><div class="wrap">
  <a class="marca" href="{rel}index.html"><img src="{rel}logo.jpg" alt=""><span>Lupa Financiera</span></a>
  <nav class="menu" aria-label="Principal">
    <a href="{rel}index.html">Inicio</a><a href="{rel}promociones.html">Promociones</a><a href="{rel}cashback.html">Cashback</a><a href="{rel}descuentos.html">Descuentos</a><a href="{rel}comparador.html">Comparador</a><a href="{rel}blog/" aria-current="page">Blog</a><a href="{rel}como-lo-hacemos.html">Cómo lo hacemos</a>
  </nav>
  <a class="x" href="https://x.com/LupaFinanzas">@LupaFinanzas</a>
</div></header>
<main class="wrap">
{cuerpo}
<footer class="pie"><p><a href="{rel}aviso-legal.html">Aviso legal</a> · <a href="{rel}privacidad.html">Política de privacidad</a> · <a href="{rel}cookies.html">Política de cookies</a></p><p>Contenido informativo, no es asesoría financiera. Las cifras cambian a diario: compruébalas en la web de cada plataforma antes de comprar.</p></footer>
</main>
</body>
</html>
"""


import re
import statistics
import unicodedata


def slug_h(t):
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", t)).strip("-")[:48]


def eur(n):
    return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def etiq(f):
    e = []
    if f.get("hasta_pct"):
        e.append("máximo anunciado («hasta»)")
    if f["tipo"] == "aumentado":
        e.append(f"subida temporal (habitual {pc(f['habitual_pct'])})")
    if f["tipo"] == "bienvenida" or f.get("solo_clientes_nuevos"):
        e.append("solo clientes nuevos")
    if f.get("primera_compra"):
        e.append("solo la primera compra")
    if f["tipo"] == "categoria":
        e.append("depende de la categoría")
    if f.get("tope") is not None:
        e.append(f"tope {eur(f['tope'])}")
    return "; ".join(e) if e else "tarifa habitual"


def tabla_tienda(slug):
    t = tiendas.get(slug)
    if not t:
        return ""
    filas = sorted(t["filas"], key=lambda f: -(min(50 * f["pct"] / 100, f["tope"]) if f.get("tope") is not None else 50 * f["pct"] / 100))
    leido = max(f["leido"] for f in filas)
    fs = "".join(f'<tr><td><a href="{esc(f["fuente"])}" rel="noopener nofollow">{esc(f["plataforma"])}</a>' + (f' ({esc(f["variante"])})' if f.get("variante") else "") +
                 f'</td><td><b>{"hasta " if f.get("hasta_pct") else ""}{pc(f["pct"])}</b></td><td>{esc(etiq(f))}</td></tr>' for f in filas)
    return (f'<h2 id="{slug_h(t["nombre"])}">Cashback en {esc(t["nombre"])}</h2><div class="tabla"><table><thead><tr><th>Plataforma</th><th>Cashback</th><th>Condiciones</th></tr></thead><tbody>{fs}</tbody></table></div>'
            f'<p class="mini">Datos leídos el {fecha(leido)}. <a href="../../tienda/{slug}/">Ver la ficha completa de {esc(t["nombre"])}</a> con los euros que recibirías y los descuentos vigentes.</p>')


def tabla_plataformas():
    por = {}
    for t in data["tiendas"]:
        for f in t["filas"]:
            if not f.get("hasta_pct") and f["tipo"] != "bienvenida" and not f.get("solo_clientes_nuevos") and not f.get("primera_compra"):
                por.setdefault(f["plataforma"], []).append(f["pct"])
    filas = sorted(((p, len(v), statistics.median(v)) for p, v in por.items()), key=lambda x: -x[1])
    fs = "".join(f"<tr><td>{esc(p)}</td><td>{n}</td><td>{pc(round(m, 2))}</td></tr>" for p, n, m in filas)
    return ('<div class="tabla"><table><thead><tr><th>Plataforma</th><th>Tarifas exactas comparadas</th><th>Mediana de cashback</th></tr></thead><tbody>' + fs +
            f'</tbody></table></div><p class="mini">Cálculo propio a {fecha(data["actualizado"])} con las tarifas exactas leídas (sin «hasta» ni ofertas solo para clientes nuevos). La mediana depende del tipo de tiendas que cubre cada plataforma: no significa que una plataforma sea mejor que otra para tu compra.</p>')


def sustituir(txt):
    n_sub = len({t["slug"] for t in data["tiendas"] for f in t["filas"] if f["tipo"] == "aumentado" and f.get("habitual_pct", 99) < f["pct"] and f["pct"] < 40})
    exactas = [f["pct"] for t in data["tiendas"] for f in t["filas"] if not f.get("hasta_pct") and f["tipo"] != "bienvenida" and not f.get("solo_clientes_nuevos") and not f.get("primera_compra")]
    return (txt.replace("{{n_tiendas}}", f"{len(data['tiendas']):,}".replace(",", "."))
            .replace("{{n_plataformas}}", str(len({f["plataforma"] for t in data["tiendas"] for f in t["filas"]})))
            .replace("{{n_subidas}}", str(n_sub)).replace("{{mediana}}", pc(round(statistics.median(exactas), 2)))
            .replace("{{fecha}}", fecha(data["actualizado"])))


urls = [(f"{SITIO}/", None), (f"{SITIO}/promociones.html", None), (f"{SITIO}/cashback.html", None), (f"{SITIO}/descuentos.html", None), (f"{SITIO}/comparador.html", None), (f"{SITIO}/como-lo-hacemos.html", None), (f"{SITIO}/blog/", None)]
indice = []
for a in arts:
    bloques = []
    toc = []
    for b in a["bloques"]:
        if "h" in b:
            hid = slug_h(b["h"])
            toc.append((hid, b["h"]))
            extra = ""
            for sl in b.get("tiendas", []):
                if sl in tiendas:
                    extra += tabla_tienda(sl).replace("<h2 ", "<h3 ").replace("</h2>", "</h3>") + "\n"
                    toc.append((slug_h(tiendas[sl]["nombre"]), f"Cashback en {tiendas[sl]['nombre']}"))
            bloques.append(f'<h2 id="{hid}">{esc(b["h"])}</h2>\n{sustituir(b["html"])}\n{extra}')
        else:
            bloques.append(sustituir(b["html"]) + "\n")
    cuerpo = "".join(bloques)
    if a.get("plataformas"):
        toc.append(("plataformas", a.get("plataformas_titulo", "Plataformas comparadas")))
        cuerpo += f'<h2 id="plataformas">{esc(a.get("plataformas_titulo", "Plataformas comparadas"))}</h2>\n' + tabla_plataformas() + "\n"
    for s in a.get("tiendas", []):
        if s in tiendas:
            toc.append((slug_h(tiendas[s]["nombre"]), f"Cashback en {tiendas[s]['nombre']}"))
            cuerpo += tabla_tienda(s) + "\n"
    if a.get("tabla"):
        toc.append(("tabla", a["tabla_titulo"]))
        cuerpo += f'<h2 id="tabla">{esc(a["tabla_titulo"])}</h2>\n' + tabla(a["tabla"]) + "\n"
    if a.get("cierre"):
        cuerpo += sustituir(a["cierre"]) + "\n"
    faq = a.get("faq", [])
    if faq:
        toc.append(("preguntas-frecuentes", "Preguntas frecuentes"))
        cuerpo += '<h2 id="preguntas-frecuentes">Preguntas frecuentes</h2>\n' + "".join(f"<details><summary>{esc(q)}</summary><p>{esc(sustituir(r))}</p></details>" for q, r in faq) + "\n"
    cuerpo += IGRAAL_CAJA.format(rel="../../") + "\n"
    cuerpo += '<div class="caja"><b>Compáralo tú mismo.</b> <a href="../../comparador.html">Abre el comparador</a>, busca tu tienda y ordena por euros recibidos, o mira las <a href="../../tienda/">fichas por tienda</a>.</div>\n'
    otros = [x for x in arts if x["slug"] != a["slug"]][:3]
    if otros:
        cuerpo += '<h2>Sigue leyendo</h2><ul>' + "".join(f'<li><a href="../{x["slug"]}/">{esc(x["titulo"])}</a></li>' for x in otros) + "</ul>\n"
    indice_toc = ""
    if len(toc) >= 4:
        indice_toc = '<nav class="caja" aria-label="Índice"><b>En este artículo</b><ul>' + "".join(f'<li><a href="#{h}">{esc(t)}</a></li>' for h, t in toc) + "</ul></nav>"
    grafo = [
        {"@type": "Article", "headline": a["titulo"], "description": a["descripcion"], "datePublished": a["fecha"], "dateModified": data["actualizado"],
         "inLanguage": "es", "image": SITIO + "/og.png", "mainEntityOfPage": f"{SITIO}/blog/{a['slug']}/",
         "author": {"@type": "Organization", "name": "Lupa Financiera", "url": SITIO + "/"},
         "publisher": {"@type": "Organization", "name": "Lupa Financiera", "logo": {"@type": "ImageObject", "url": SITIO + "/logo.jpg"}}},
        {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Inicio", "item": SITIO + "/"},
                                                        {"@type": "ListItem", "position": 2, "name": "Blog", "item": SITIO + "/blog/"},
                                                        {"@type": "ListItem", "position": 3, "name": a["titulo"], "item": f"{SITIO}/blog/{a['slug']}/"}]}]
    if faq:
        grafo.append({"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": sustituir(r)}} for q, r in faq]})
    jsonld = '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@graph": grafo}, ensure_ascii=False) + "</script>"
    cab = (f'<article class="art"><nav class="mini" aria-label="Migas de pan"><a href="../../index.html">Inicio</a> › <a href="../">Blog</a></nav>'
           f'<span class="mini">Actualizado {fecha(data["actualizado"])} · publicado {fecha(a["fecha"])}</span><h1>{esc(a["titulo"])}</h1><p class="sub">{esc(a["descripcion"])}</p>\n{indice_toc}\n{cuerpo}</article>')
    out = BASE / "blog" / a["slug"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(pagina(f"blog/{a['slug']}/", a["titulo"], a["descripcion"], cab, jsonld), encoding="utf-8")
    urls.append((f"{SITIO}/blog/{a['slug']}/", data["actualizado"]))
    indice.append(f'<a class="card" href="{a["slug"]}/"><span class="mini">{fecha(a["fecha"])}</span><h2>{esc(a["titulo"])}</h2><p>{esc(a["descripcion"])}</p></a>')

cab = f'<div class="art"><span class="mini">Blog</span><h1>Cashback y ahorro con datos reales</h1><p class="sub">Guías basadas en las cifras que leemos cada día en las plataformas, sin promesas de dinero fácil.</p><div class="lista">{"".join(indice)}</div></div>'
(BASE / "blog").mkdir(exist_ok=True)
(BASE / "blog" / "index.html").write_text(pagina("blog/", "Blog de cashback y ahorro", "Guías sobre cashback y ahorro en compras online en España, con cifras leídas y comprobadas cada día.", cab), encoding="utf-8")

mapa = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for u, lm in urls:
    mapa.append(f"<url><loc>{u}</loc>" + (f"<lastmod>{lm}</lastmod>" if lm else "") + "</url>")
mapa.append("</urlset>")
(BASE / "sitemap.xml").write_text("\n".join(mapa) + "\n", encoding="utf-8")
print(f"{len(arts)} artículos, {len(urls)} URLs en el sitemap")
