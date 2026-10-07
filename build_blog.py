"""Genera el blog (blog/index.html, blog/<slug>/index.html), sitemap.xml y robots.txt.

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
    <a href="{rel}index.html">Promos</a><a href="{rel}comparador.html">Comparador</a><a href="{rel}blog/" aria-current="page">Blog</a><a href="{rel}como-lo-hacemos.html">Cómo lo hacemos</a>
  </nav>
  <a class="x" href="https://x.com/LupaFinanzas">@LupaFinanzas</a>
</div></header>
<main class="wrap">
{cuerpo}
<footer class="pie"><p>Contenido informativo, no es asesoría financiera. Las cifras cambian a diario: compruébalas en la web de cada plataforma antes de comprar.</p></footer>
</main>
</body>
</html>
"""


urls = [(f"{SITIO}/", None), (f"{SITIO}/comparador.html", None), (f"{SITIO}/como-lo-hacemos.html", None), (f"{SITIO}/blog/", None)]
indice = []
for a in arts:
    cuerpo = "".join(f"<h2>{esc(b['h'])}</h2>\n{b['html']}\n" if "h" in b else b["html"] + "\n" for b in a["bloques"])
    if a.get("tabla"):
        cuerpo += f"<h2>{esc(a['tabla_titulo'])}</h2>\n" + tabla(a["tabla"]) + "\n"
    if a.get("cierre"):
        cuerpo += a["cierre"] + "\n"
    cuerpo += '<div class="caja"><b>Compáralo tú mismo.</b> <a href="../../comparador.html">Abre el comparador</a>, busca tu tienda y ordena por euros recibidos.</div>\n'
    jsonld = '<script type="application/ld+json">' + json.dumps({
        "@context": "https://schema.org", "@type": "Article", "headline": a["titulo"], "description": a["descripcion"],
        "datePublished": a["fecha"], "dateModified": data["actualizado"], "inLanguage": "es",
        "mainEntityOfPage": f"{SITIO}/blog/{a['slug']}/", "author": {"@type": "Organization", "name": "Lupa Financiera"},
        "publisher": {"@type": "Organization", "name": "Lupa Financiera", "logo": {"@type": "ImageObject", "url": f"{SITIO}/logo.jpg"}},
    }, ensure_ascii=False) + "</script>"
    cab = f'<article class="art"><span class="mini">Blog · {fecha(a["fecha"])}</span><h1>{esc(a["titulo"])}</h1><p class="sub">{esc(a["descripcion"])}</p>\n{cuerpo}</article>'
    out = BASE / "blog" / a["slug"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(pagina(f"blog/{a['slug']}/", a["titulo"], a["descripcion"], cab, jsonld), encoding="utf-8")
    urls.append((f"{SITIO}/blog/{a['slug']}/", data["actualizado"]))
    indice.append(f'<a class="card" href="{a["slug"]}/"><span class="mini">{fecha(a["fecha"])}</span><h2>{esc(a["titulo"])}</h2><p>{esc(a["descripcion"])}</p></a>')

cab = f'<div class="art"><span class="mini">Blog</span><h1>Cashback y ahorro con datos reales</h1><p class="sub">Guías cortas basadas en las cifras que leemos cada día en las plataformas, sin promesas de dinero fácil.</p><div class="lista">{"".join(indice)}</div></div>'
(BASE / "blog").mkdir(exist_ok=True)
(BASE / "blog" / "index.html").write_text(pagina("blog/", "Blog de cashback y ahorro", "Guías sobre cashback y ahorro en compras online en España, con cifras leídas y comprobadas cada día.", cab), encoding="utf-8")

mapa = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for u, lm in urls:
    mapa.append(f"<url><loc>{u}</loc>" + (f"<lastmod>{lm}</lastmod>" if lm else "") + "</url>")
mapa.append("</urlset>")
(BASE / "sitemap.xml").write_text("\n".join(mapa) + "\n", encoding="utf-8")
(BASE / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /ir/\nSitemap: {SITIO}/sitemap.xml\n", encoding="utf-8")
print(f"{len(arts)} artículos, {len(urls)} URLs en el sitemap")
