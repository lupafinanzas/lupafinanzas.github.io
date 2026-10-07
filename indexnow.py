"""Avisa a Bing y a otros buscadores compatibles (IndexNow) de las URLs que han cambiado, para que las rastreen cuanto antes.

Uso: python indexnow.py            (URLs del sitemap con lastmod de hoy; si no hay ninguna, las páginas principales)
     python indexnow.py --todas    (todas las URLs del sitemap)
Necesita el archivo de clave publicado en la raíz de la web (<clave>.txt con la propia clave dentro); la clave está en datos/indexnow_clave.txt.
Solo envía direcciones públicas del propio sitio. No lleva datos personales.
"""
import datetime
import json
import pathlib
import re
import sys
import urllib.request

from util_rutas import datos

base = pathlib.Path(__file__).parent
HOST = "lupafinanzas.github.io"
clave = datos("indexnow_clave.txt").read_text(encoding="utf-8").strip()
hoy = datetime.date.today().isoformat()
mapa = (base / "sitemap.xml").read_text(encoding="utf-8")
todas = re.findall(r"<url><loc>([^<]+)</loc>(?:<lastmod>([^<]*)</lastmod>)?</url>", mapa)
urls = [u for u, lm in todas if "--todas" in sys.argv or lm == hoy]
if not urls:
    urls = [f"https://{HOST}/", f"https://{HOST}/promociones.html", f"https://{HOST}/cashback.html", f"https://{HOST}/descuentos.html"]
urls = urls[:9000]
cuerpo = json.dumps({"host": HOST, "key": clave, "keyLocation": f"https://{HOST}/{clave}.txt", "urlList": urls}).encode("utf-8")
req = urllib.request.Request("https://api.indexnow.org/indexnow", data=cuerpo, headers={"Content-Type": "application/json; charset=utf-8"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("IndexNow:", r.status, f"{len(urls)} URLs enviadas")
except Exception as e:
    print("IndexNow no disponible:", e)
