"""Genera una página por categoría (categoria/<slug>/index.html) y el índice categoria/index.html con las tarifas de hoy.

Uso: python build_categorias.py   (después de leer_categorias.py y de actualizar cashback.json; antes de prerender.py)
Une cada tienda con su categoría de Beruby por el slug de la ficha de Beruby (campo «fuente» de las filas de Beruby).
Todo el contenido sale de los datos leídos, con su fecha. Solo se crean categorías con 8 o más tiendas con tarifa exacta.
"""
import datetime
import html
import json
import pathlib
import re
import statistics

BASE = pathlib.Path(__file__).parent
SITIO = "https://lupafinanzas.github.io"
esc = html.escape
cat_path = BASE / "datos" / "categorias.json"
if not cat_path.exists():
    raise SystemExit("Falta datos/categorias.json: ejecuta leer_categorias.py")
CAT = json.loads(cat_path.read_text(encoding="utf-8"))
data = json.loads((BASE / "cashback.json").read_text(encoding="utf-8"))
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
ETIQUETAS = {
    "compras-moda": ("moda", "Moda y calzado"), "compras-salud-y-belleza": ("salud y belleza", "Salud y belleza"),
    "compras-tecnologia": ("tecnología", "Tecnología"), "compras-hogar": ("hogar", "Hogar"), "compras-deportes": ("deporte", "Deporte"),
    "compras-ocio": ("ocio", "Ocio"), "compras-multitienda": ("grandes tiendas", "Grandes tiendas"), "compras-infantil": ("infantil", "Infantil"),
    "compras-alimentacion": ("alimentación", "Alimentación"), "compras-motor": ("motor", "Motor"), "compras-regalos": ("regalos", "Regalos"),
    "compras-oficina": ("oficina", "Oficina"), "compras-mascotas": ("mascotas", "Mascotas"), "viajes-hoteles": ("hoteles", "Hoteles"),
    "viajes-otros-sitios-de-viajes": ("viajes", "Viajes"), "viajes-alquiler-de-coches": ("alquiler de coches", "Alquiler de coches"),
    "viajes-agencias-de-viajes": ("agencias de viajes", "Agencias de viajes"), "viajes-companias-aereas": ("aerolíneas", "Aerolíneas"),
}


def fecha(iso):
    a, m, d = iso.split("-")
    return f"{int(d)} de {MESES[int(m) - 1]} de {a}"


def pc(n):
    return f"{n:g}".replace(".", ",") + " %"


def eur(n):
    return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def nuevo(f):
    return f["tipo"] == "bienvenida" or f.get("solo_clientes_nuevos") or f.get("primera_compra")


# slug de Beruby -> tienda nuestra
por_beruby = {}
for t in data["tiendas"]:
    for f in t["filas"]:
        if f["plataforma"] == "Beruby":
            por_beruby[f["fuente"].rstrip("/").rsplit("/", 1)[-1]] = t
ficha = {x.name for x in (BASE / "tienda").iterdir() if x.is_dir()} if (BASE / "tienda").exists() else set()

CSS = """<style>
.art{max-width:820px;margin:0 auto;padding:24px 16px 8px}.art h1{font-size:clamp(1.8rem,6vw,2.5rem);margin:6px 0 12px}.art h2{font-size:1.35rem;margin:28px 0 8px}.art p{margin:8px 0}
.tabla{overflow-x:auto;margin:14px 0;border:1px solid var(--line);border-radius:16px;background:var(--card)}.tabla table{width:100%;border-collapse:collapse;font-size:.92rem}
.tabla th,.tabla td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line)}.tabla tr:last-child td{border-bottom:0}
.art details{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 16px;margin:10px 0}.art summary{cursor:pointer;font-weight:800}
.lista{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:8px;margin:14px 0}.lista a{display:block;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 12px;text-decoration:none}
</style>"""
MENU = ('<a href="{r}index.html">Inicio</a><a href="{r}promociones.html">Promociones</a><a href="{r}cashback.html">Cashback</a><a href="{r}descuentos.html">Descuentos</a>'
        '<a href="{r}comparador.html">Comparador</a><a href="{r}blog/">Blog</a><a href="{r}como-lo-hacemos.html">Cómo lo hacemos</a>')


def pagina(ruta, titulo, desc, cuerpo, jsonld, r):
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(titulo)}</title><meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITIO}/{ruta}"><meta property="og:title" content="{esc(titulo)}"><meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website"><meta property="og:url" content="{SITIO}/{ruta}"><meta property="og:image" content="{SITIO}/og.png"><meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0b2e25"><link rel="icon" href="{r}logo.jpg"><link rel="stylesheet" href="{r}fuentes.css"><link rel="stylesheet" href="{r}estilo.css">{CSS}
<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script></head><body>
<header class="top"><div class="wrap"><a class="marca" href="{r}index.html"><img src="{r}logo.jpg" alt=""><span>Lupa Financiera</span></a><nav class="menu" aria-label="Principal">{MENU.format(r=r)}</nav><a class="x" href="https://x.com/LupaFinanzas">@LupaFinanzas</a></div></header>
<main class="wrap">{cuerpo}<footer class="pie"><p><a href="{r}aviso-legal.html">Aviso legal</a> · <a href="{r}privacidad.html">Política de privacidad</a> · <a href="{r}cookies.html">Política de cookies</a></p><p>Datos orientativos leídos de fuentes públicas con su fecha. No es asesoría financiera.</p></footer></main></body></html>"""


leido = data["actualizado"]
creadas, indice = [], []
for cat, slugs_b in CAT["categorias"].items():
    if cat not in ETIQUETAS:
        continue
    corto, largo = ETIQUETAS[cat]
    filas = []
    for sb in slugs_b:
        t = por_beruby.get(sb)
        if not t:
            continue
        ex = [f for f in t["filas"] if not f.get("hasta_pct") and not nuevo(f) and f["tipo"] != "categoria" and f["pct"] < 60]
        if not ex:
            continue
        mejor = max(ex, key=lambda f: f["pct"])
        filas.append((mejor["pct"], t, mejor, len({f["plataforma"] for f in t["filas"]})))
    if len(filas) < 8:
        continue
    filas.sort(key=lambda x: (-x[0], x[1]["nombre"].lower()))
    mediana = statistics.median(p for p, _, _, _ in filas)
    top = filas[:40]
    trs = "".join(
        f'<tr><td>' + (f'<a href="../../tienda/{t["slug"]}/">{esc(t["nombre"])}</a>' if t["slug"] in ficha else f'<a href="../../comparador.html#{esc(t["slug"])}">{esc(t["nombre"])}</a>') +
        f'</td><td><b>{pc(p)}</b></td><td>{esc(f["plataforma"])}</td><td>{eur(50 * p / 100 if f.get("tope") is None else min(50 * p / 100, f["tope"]))}</td><td>{n}</td></tr>'
        for p, t, f, n in top)
    faq = [(f"¿Cuánto cashback devuelven las tiendas de {corto}?",
            f"A {fecha(leido)}, la mediana de las mejores tarifas exactas que leemos en {len(filas)} tiendas de {corto} es {pc(mediana)}. Varía mucho de una tienda a otra: mira la tabla."),
           (f"¿Qué plataforma da más cashback en {corto}?", "Depende de cada tienda y cambia a diario. En la tabla indicamos, para cada tienda, la plataforma con la mejor tarifa exacta de hoy; en su ficha las comparamos todas."),
           ("¿Qué significa «tarifa exacta»?", "Es el porcentaje fijo que publica la ficha de la plataforma, sin «hasta» (máximos anunciados) y sin ofertas solo para clientes nuevos o primera compra.")]
    cuerpo = (f'<article class="art"><nav class="mini" aria-label="Migas de pan"><a href="../../index.html">Inicio</a> › <a href="../">Categorías</a> › {esc(largo)}</nav>'
              f'<h1>Cashback en {esc(corto)}: las mejores tarifas de hoy</h1>'
              f'<p class="sub">A {fecha(leido)} comparamos {len(filas)} tiendas de {esc(corto)}. La mediana de la mejor tarifa exacta es {pc(mediana)}. Cada cifra se lee en la ficha pública de la plataforma, con doble comprobación.</p>'
              f'<div class="tabla"><table><thead><tr><th>Tienda</th><th>Mejor tarifa</th><th>Plataforma</th><th>Con 50 €</th><th>Plataformas</th></tr></thead><tbody>{trs}</tbody></table></div>'
              f'<p class="mini">Se muestran las {len(top)} tiendas con mayor tarifa exacta. Sin «hasta», sin ofertas solo para clientes nuevos y sin cifras por encima del 60 %, que revisamos a mano. Cálculo orientativo, sin IVA ni envío.</p>'
              f'<h2>Preguntas frecuentes</h2>' + "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faq) +
              f'<p class="mini"><a href="../../comparador.html">Comparador</a> · <a href="../../calculadora.html">Calculadora de ahorro</a> · <a href="../../plataformas/">Plataformas</a> · <a href="../../blog/">Guías</a></p></article>')
    titulo = f"Cashback en {corto}: mejores tarifas hoy · Lupa Financiera"
    desc = f"Cashback en {len(filas)} tiendas de {corto}: mediana {pc(mediana)} y mejores tarifas exactas de hoy, con plataforma y fecha de lectura ({fecha(leido)})."[:158]
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Inicio", "item": SITIO + "/"}, {"@type": "ListItem", "position": 2, "name": "Categorías", "item": SITIO + "/categoria/"}, {"@type": "ListItem", "position": 3, "name": largo, "item": f"{SITIO}/categoria/{cat}/"}]},
        {"@type": "ItemList", "name": f"Cashback en {corto}", "itemListElement": [{"@type": "ListItem", "position": i, "name": t["nombre"]} for i, (_, t, _, _) in enumerate(top[:20], 1)]},
        {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}]}
    out = BASE / "categoria" / cat
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(pagina(f"categoria/{cat}/", titulo, desc, cuerpo, jsonld, "../../"), encoding="utf-8")
    creadas.append(cat)
    indice.append((largo, cat, len(filas), mediana))

cuerpo = ('<article class="art"><h1>Cashback por categoría</h1><p class="sub">Elige una categoría para ver las tiendas con mayor cashback exacto hoy.</p><div class="lista">'
          + "".join(f'<a href="{c}/"><b>{esc(l)}</b><br><span class="mini">{n} tiendas · mediana {pc(m)}</span></a>' for l, c, n, m in sorted(indice)) + '</div></article>')
jsonld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Cashback por categoría", "inLanguage": "es", "url": SITIO + "/categoria/"}
(BASE / "categoria").mkdir(exist_ok=True)
(BASE / "categoria" / "index.html").write_text(pagina("categoria/", "Cashback por categoría · Lupa Financiera", "Cashback por categoría: moda, viajes, tecnología, hogar, deporte… con las mejores tarifas exactas de hoy y su fecha de lectura.", cuerpo, jsonld, "../"), encoding="utf-8")
mapa = BASE / "sitemap.xml"
s = mapa.read_text(encoding="utf-8")
s = re.sub(r"<url><loc>[^<]*/categoria/[^<]*</loc>(<lastmod>[^<]*</lastmod>)?</url>\n?", "", s)
extra = "".join(f"<url><loc>{SITIO}/categoria/{c}/</loc><lastmod>{leido}</lastmod></url>\n" for c in creadas) + f"<url><loc>{SITIO}/categoria/</loc><lastmod>{leido}</lastmod></url>\n"
mapa.write_text(s.replace("</urlset>", extra + "</urlset>"), encoding="utf-8")
print(f"{len(creadas)} páginas de categoría")
