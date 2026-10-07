"""Lee de Beruby en qué categoría está cada tienda (moda, viajes, tecnología…) y guarda datos/categorias.json.

Uso: python leer_categorias.py            (unas 200 páginas; ~8 minutos con la pausa de 2 s; las categorías cambian poco: una vez por semana basta)
     python leer_categorias.py --prueba   (solo la primera página de cada categoría)
Salida: datos/categorias.json -> {"actualizado": fecha, "categorias": {"compras-moda": ["slug-de-beruby", ...], ...}}
Respeta robots.txt (Crawl-delay 1 s), se identifica con su propio User-Agent y no usa sesión.
"""
import datetime
import json
import pathlib
import re
import sys
import time
import urllib.request

from bs4 import BeautifulSoup

from util_rutas import datos

UA = "LupaFinanzas-lector/1.0 (+https://lupafinanzas.github.io; lectura diaria de cashback)"
EXCLUIR = {"compras", "viajes", "compras-finanzas", "cashback-gratis-cashback-gratis"}  # padres y finanzas (fuera de este comparador)


def get(url):
    r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9"})
    with urllib.request.urlopen(r, timeout=30) as f:
        return f.read().decode("utf-8", "replace")


sm = get("https://es.beruby.com/sitemap/main")
paginas = {}
for u in re.findall(r"<loc>https://es\.beruby\.com/([^<]*)</loc>", sm):
    m = re.match(r"^((?:compras|viajes)-[a-z0-9-]+)\?page=(\d+)$", u)
    if m and m.group(1) not in EXCLUIR:
        paginas[m.group(1)] = max(paginas.get(m.group(1), 0), int(m.group(2)))
nombres_categoria = set(paginas) | EXCLUIR
resultado = {}
total = 0
for cat, n in sorted(paginas.items()):
    tiendas = []
    for i in range(1, (1 if "--prueba" in sys.argv else n) + 1):
        try:
            soup = BeautifulSoup(get(f"https://es.beruby.com/{cat}?page={i}"), "html.parser")
            for a in soup.select(".card-advertiser a[href]"):
                m = re.fullmatch(r"(?:https://es\.beruby\.com)?/([a-z0-9-]+)", a["href"])
                if m and m.group(1) not in nombres_categoria and m.group(1) not in tiendas:
                    tiendas.append(m.group(1))
        except Exception as e:
            print("error", cat, i, type(e).__name__, e, flush=True)
        total += 1
        time.sleep(2.0)
    resultado[cat] = tiendas
    print(cat, len(tiendas), "tiendas", flush=True)
salida = pathlib.Path(sys.argv[sys.argv.index("--salida") + 1]) if "--salida" in sys.argv else datos("categorias.json")
salida.write_text(json.dumps({"actualizado": datetime.date.today().isoformat(), "categorias": resultado}, ensure_ascii=False), encoding="utf-8")
print(f"{len(resultado)} categorías, {sum(len(v) for v in resultado.values())} tiendas, {total} páginas leídas")
