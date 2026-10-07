"""Genera plataformas/index.html: comparativa de plataformas de cashback con métricas propias calculadas de cashback.json.

Uso: python build_plataformas.py   (después de actualizar cashback.json; antes de prerender.py)
Todo sale de los datos leídos: tiendas cubiertas, mediana de las tarifas exactas, proporción de «hasta» y mejores tiendas. No hay valoraciones
inventadas: la «Nota Real» de las plataformas (plazo de cobro, mínimo, métodos de pago) solo se publicará cuando se pueda comprobar en sus condiciones.
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
data = json.loads((BASE / "cashback.json").read_text(encoding="utf-8"))
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def fecha(iso):
    a, m, d = iso.split("-")
    return f"{int(d)} de {MESES[int(m) - 1]} de {a}"


def pc(n):
    return f"{n:g}".replace(".", ",") + " %"


def nuevo(f):
    return f["tipo"] == "bienvenida" or f.get("solo_clientes_nuevos") or f.get("primera_compra")


por = {}
for t in data["tiendas"]:
    for f in t["filas"]:
        por.setdefault(f["plataforma"], []).append((t, f))

filas, bloques = [], []
for plat, items in sorted(por.items(), key=lambda x: -len({t["slug"] for t, _ in x[1]})):
    tiendas = {t["slug"] for t, _ in items}
    exactas = [f["pct"] for t, f in items if not f.get("hasta_pct") and not nuevo(f) and f["tipo"] != "categoria"]
    hasta = sum(1 for _, f in items if f.get("hasta_pct"))
    plazo = sum(1 for _, f in items if f.get("plazo_dias"))
    mediana = pc(round(statistics.median(exactas), 2)) if exactas else "—"
    mejores = sorted(((f["pct"], t["nombre"]) for t, f in items if not f.get("hasta_pct") and not nuevo(f) and f["pct"] < 40), reverse=True)[:5]
    fuente = items[0][1]["fuente"].split("/")[2]
    filas.append(f"<tr><td><b>{esc(plat)}</b></td><td>{len(tiendas)}</td><td>{len(exactas)}</td><td>{mediana}</td><td>{round(100 * hasta / len(items))} %</td><td>{esc(fuente)}</td></tr>")
    bloques.append(f'<h3>{esc(plat)}</h3><p>Cubre {len(tiendas)} de las tiendas que comparamos. '
                   + (f"Entre sus tarifas exactas, las más altas con tiendas de uso general son: " + ", ".join(f"{esc(n)} ({pc(p)})" for p, n in mejores) + ". " if mejores else "")
                   + (f"Publica un plazo de cobro estimado en {plazo} de sus fichas. " if plazo else "No publica un plazo de cobro estimado en las fichas que leemos. ")
                   + f"Leemos su ficha pública de cada tienda ({esc(fuente)}).</p>")

leido = data["actualizado"]
CSS = """<style>
.art{max-width:820px;margin:0 auto;padding:24px 16px 8px}.art h1{font-size:clamp(1.8rem,6vw,2.5rem);margin:6px 0 12px}.art h2{font-size:1.35rem;margin:28px 0 8px}.art h3{font-size:1.1rem;margin:18px 0 4px}.art p{margin:8px 0}
.tabla{overflow-x:auto;margin:14px 0;border:1px solid var(--line);border-radius:16px;background:var(--card)}.tabla table{width:100%;border-collapse:collapse;font-size:.92rem}
.tabla th,.tabla td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line)}.tabla tr:last-child td{border-bottom:0}
.art details{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 16px;margin:10px 0}.art summary{cursor:pointer;font-weight:800}
</style>"""
MENU = ('<a href="../index.html">Inicio</a><a href="../promociones.html">Promociones</a><a href="../cashback.html">Cashback</a><a href="../descuentos.html">Descuentos</a>'
        '<a href="../comparador.html">Comparador</a><a href="../blog/">Blog</a><a href="../como-lo-hacemos.html">Cómo lo hacemos</a>')
faq = [("¿Cuál es la mejor plataforma de cashback?", "Depende de la tienda y del día: la que más devuelve cambia. Usa el comparador para tu tienda y tu importe."),
       ("¿Por qué las plataformas pagan porcentajes distintos por la misma tienda?", "Cada plataforma negocia su comisión con la tienda y decide cuánto te devuelve."),
       ("¿Qué significa la mediana de cashback?", "Es el porcentaje central de las tarifas exactas que leemos en esa plataforma: la mitad paga más y la mitad menos. Depende de las tiendas que cubre, no mide su calidad.")]
desc = f"Comparativa de {len(por)} plataformas de cashback en España con datos propios: tiendas cubiertas, mediana de tarifas y mejores tiendas. Datos del {fecha(leido)}."
cuerpo = (f'<article class="art"><nav class="mini" aria-label="Migas de pan"><a href="../index.html">Inicio</a> › Plataformas</nav>'
          f'<h1>Plataformas de cashback comparadas</h1><p class="sub">{len(por)} plataformas, {len(data["tiendas"])} tiendas. Cada cifra sale de la ficha pública de la plataforma, leída y comprobada, con fecha ({fecha(leido)}).</p>'
          f'<div class="tabla"><table><thead><tr><th>Plataforma</th><th>Tiendas</th><th>Tarifas exactas</th><th>Mediana</th><th>Filas «hasta»</th><th>Fuente</th></tr></thead><tbody>{"".join(filas)}</tbody></table></div>'
          f'<p class="mini">«Tarifas exactas» excluye los máximos anunciados («hasta»), las ofertas solo para clientes nuevos y las tarifas por categoría. La mediana depende de las tiendas que cubre cada plataforma: no es una nota de calidad.</p>'
          f'<h2>Qué destaca de cada una</h2>{"".join(bloques)}'
          f'<h2>Preguntas frecuentes</h2>' + "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faq) +
          f'<p class="mini">Para tu tienda, ve al <a href="../comparador.html">comparador</a> o a las <a href="../tienda/">fichas por tienda</a>. Guía para elegir: <a href="../blog/mejores-plataformas-de-cashback-en-espana/">mejores plataformas de cashback en España</a>.</p></article>')
jsonld = {"@context": "https://schema.org", "@graph": [
    {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Inicio", "item": SITIO + "/"}, {"@type": "ListItem", "position": 2, "name": "Plataformas", "item": SITIO + "/plataformas/"}]},
    {"@type": "WebPage", "name": "Plataformas de cashback comparadas", "description": desc, "inLanguage": "es", "dateModified": leido},
    {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}]}
pagina = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Plataformas de cashback comparadas · Lupa Financiera</title><meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITIO}/plataformas/"><meta property="og:title" content="Plataformas de cashback comparadas"><meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website"><meta property="og:url" content="{SITIO}/plataformas/"><meta property="og:image" content="{SITIO}/og.png"><meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0b2e25"><link rel="icon" href="../logo.jpg"><link rel="stylesheet" href="../fuentes.css"><link rel="stylesheet" href="../estilo.css">{CSS}
<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script></head><body>
<header class="top"><div class="wrap"><a class="marca" href="../index.html"><img src="../logo.jpg" alt=""><span>Lupa Financiera</span></a><nav class="menu" aria-label="Principal">{MENU}</nav><a class="x" href="https://x.com/LupaFinanzas">@LupaFinanzas</a></div></header>
<main class="wrap">{cuerpo}<footer class="pie"><p><a href="../aviso-legal.html">Aviso legal</a> · <a href="../privacidad.html">Política de privacidad</a> · <a href="../cookies.html">Política de cookies</a></p><p>Datos orientativos leídos de fuentes públicas con su fecha. No es asesoría financiera.</p></footer></main></body></html>"""
out = BASE / "plataformas"
out.mkdir(exist_ok=True)
(out / "index.html").write_text(pagina, encoding="utf-8")

mapa = BASE / "sitemap.xml"
s = mapa.read_text(encoding="utf-8")
s = re.sub(r"<url><loc>[^<]*/plataformas/</loc>(<lastmod>[^<]*</lastmod>)?</url>\n?", "", s)
s = s.replace("</urlset>", f"<url><loc>{SITIO}/plataformas/</loc><lastmod>{leido}</lastmod></url>\n</urlset>")
mapa.write_text(s, encoding="utf-8")
print(f"plataformas/index.html: {len(por)} plataformas")
