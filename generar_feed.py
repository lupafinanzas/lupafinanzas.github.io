"""Genera feed.xml (RSS 2.0) con las guías del blog y una entrada diaria con las subidas de cashback.

Uso: python generar_feed.py   (después de build_blog.py)
"""
import datetime
import email.utils
import html
import json
import pathlib

base = pathlib.Path(__file__).parent
SITIO = "https://lupafinanzas.github.io"
esc = html.escape
arts = json.loads((base / "blog_src" / "articulos.json").read_text(encoding="utf-8"))
cb = json.loads((base / "cashback.json").read_text(encoding="utf-8"))


def rfc(iso):
    d = datetime.datetime.fromisoformat(iso).replace(tzinfo=datetime.timezone.utc)
    return email.utils.format_datetime(d)


items = []
subidas = [(t["nombre"], f) for t in cb["tiendas"] for f in t["filas"]
           if f["tipo"] == "aumentado" and f.get("habitual_pct", 99) < f["pct"] and f["pct"] < 40 and not f.get("solo_clientes_nuevos")]
subidas.sort(key=lambda x: -x[1]["pct"])
if subidas:
    resumen = "; ".join(f"{n}: {f['pct']:g} % con {f['plataforma']} (antes {f['habitual_pct']:g} %)".replace(".", ",") for n, f in subidas[:8])
    items.append((cb["actualizado"], f"Cashback de hoy: {len(subidas)} subidas temporales", f"{SITIO}/cashback.html#subidas",
                  f"Subidas de cashback leídas el {cb['actualizado']}: {resumen}."))
for a in sorted(arts, key=lambda x: x["fecha"], reverse=True):
    items.append((a["fecha"], a["titulo"], f"{SITIO}/blog/{a['slug']}/", a["descripcion"]))
xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<rss version="2.0"><channel>',
       "<title>Lupa Financiera</title>", f"<link>{SITIO}/</link>",
       "<description>Cashback y descuentos comprobados dos veces: novedades diarias y guías.</description>", "<language>es</language>"]
for fecha, titulo, enlace, desc in items:
    xml.append(f"<item><title>{esc(titulo)}</title><link>{enlace}</link><guid>{enlace}#{fecha}</guid><pubDate>{rfc(fecha)}</pubDate><description>{esc(desc)}</description></item>")
xml.append("</channel></rss>")
(base / "feed.xml").write_text("\n".join(xml) + "\n", encoding="utf-8")
print("feed.xml:", len(items), "entradas")
