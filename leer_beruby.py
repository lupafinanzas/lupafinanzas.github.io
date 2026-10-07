"""Lector de Beruby en Python (sin navegador). Equivale a lector_beruby.js y escribe directamente los archivos para el importador.

Uso: python leer_beruby.py            (lee todo el sitemap, ~1.700 fichas; unos 60 minutos con la pausa de 2 s)
     python leer_beruby.py --prueba   (solo las 30 primeras fichas)
Salida: cambios_beruby.txt y fallos_beruby.txt en esta carpeta; después: python importar_beruby.py cambios_beruby.txt --refrescar fallos_beruby.txt
Respeta robots.txt de Beruby (Crawl-delay 1 s; aquí 2 s), se identifica con su propio User-Agent y no usa sesión ni credenciales.
Doble lectura (misma página, dos vías): A = bloques .item-earning del DOM; B = los <span class="number"> del HTML crudo.
Deben coincidir y la ficha debe titularse "Cashback en <tienda>". Sin cashback (0 %) no se genera fila.
"""
import json
import pathlib
import re
import sys
import time
import urllib.request

from bs4 import BeautifulSoup

base = pathlib.Path(__file__).parent
UA = "LupaFinanzas-lector/1.0 (+https://lupafinanzas.github.io; lectura diaria de cashback)"
PAUSA = 2.0
NO_TIENDA = re.compile(r"^(blog|web|sitemap|cashback-novedades|ofertas-en-la-red|compras.*|viajes.*|lo-mas-buscado.*)$")


def get(url):
    r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9"})
    with urllib.request.urlopen(r, timeout=30) as f:
        return f.status, f.read().decode("utf-8", "replace")


def num(s):
    return float(s.replace("%", "").replace(",", ".").strip())


# lo publicado hoy: {slug: [pct, ...]}
publicado = {}
data = json.loads((base / "cashback.json").read_text(encoding="utf-8"))
for t in data["tiendas"]:
    for f in t["filas"]:
        if f["plataforma"] == "Beruby":
            publicado.setdefault(f["fuente"].rstrip("/").split("/")[-1], []).append(f["pct"])

_, sm = get("https://es.beruby.com/sitemap/main")
slugs = [s for s in re.findall(r"<loc>https://es\.beruby\.com/([a-z0-9-]+)</loc>", sm) if not NO_TIENDA.match(s)]
if "--prueba" in sys.argv:
    slugs = slugs[:30]
print(len(slugs), "fichas a leer")

cambios, vistos, errores = [], set(), 0
for i, s in enumerate(slugs, 1):
    try:
        st, t = get("https://es.beruby.com/" + s)
        if st == 200:
            soup = BeautifulSoup(t, "html.parser")
            h1 = soup.find("h1")
            m = re.match(r"^Cashback en (.+)$", re.sub(r"\s+", " ", h1.get_text()).strip()) if h1 else None
            tar = []
            for e in soup.select(".item-earning"):
                tit, n = e.select_one(".title"), e.select_one(".number")
                if tit and n and re.fullmatch(r"\d+(?:[.,]\d+)?%", n.get_text().strip()):
                    tar.append((re.sub(r"\s+", " ", tit.get_text()).strip(), n.get_text().strip()))
            crudo = re.findall(r'<span class="number[^"]*">\s*(\d+(?:[.,]\d+)?%)\s*</span>', t)
            if m and tar and len(tar) == len(crudo) and all(a[1] == b for a, b in zip(tar, crudo)):
                vistos.add(s)
                pos = [x for x in tar if num(x[1]) > 0]
                if not pos and s in publicado:
                    vistos.discard(s)
                sig = sorted(num(x[1]) for x in pos)
                if pos and sig != sorted(publicado.get(s, [])):
                    nombre = m.group(1).replace("|", "/")
                    for tit, n in pos:
                        nuevos = 1 if re.search(r"cliente nuevo|nuevos clientes|primera compra", tit, re.I) else 0
                        tope = re.search(r"máximo por transacción:\s*(\d+(?:[.,]\d+)?)\s*€", tit, re.I)
                        variante = re.sub(r"\s*\(.*?\)\s*", " ", tit).replace("|", "/").strip()
                        cambios.append("|".join([s, nombre, variante, f"{num(n):g}", str(nuevos), f"{num(tope.group(1)):g}" if tope else "",
                                                 "Bloque de la ficha: " + tit.replace("|", "/") + " " + n, "HTML de la ficha: " + n]))
    except Exception as e:  # ficha no leída: cuenta como fallo si estaba publicada
        errores += 1
        if errores <= 3:
            print('error en', s, type(e).__name__, e, flush=True)
    if i % 100 == 0:
        print(i, "/", len(slugs), flush=True)
    time.sleep(PAUSA)

fallos = [s for s in publicado if s not in vistos]
(base / "cambios_beruby.txt").write_text("\n".join(cambios) + "\n", encoding="utf-8")
(base / "fallos_beruby.txt").write_text("\n".join(fallos) + "\n", encoding="utf-8")
print(f"listo: {len(cambios)} tarifas en cambios, {len(fallos)} fallos, {errores} errores de red")
