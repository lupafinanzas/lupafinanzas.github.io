"""Lector de TopCashback en Python (sin navegador). Escribe directamente los archivos para importar_topcashback.py.

Uso: python leer_topcashback.py            (unas 360 fichas; ~12 minutos con la pausa de 2 s)
     python leer_topcashback.py --prueba   (solo 12 fichas)
Salida: cambios_topcashback.txt y fallos_topcashback.txt en esta carpeta; después:
        python importar_topcashback.py cambios_topcashback.txt --refrescar fallos_topcashback.txt
Fichas: https://www.topcashback.es/<slug>/ (su robots.txt solo veta /ref/ y /share/). Se identifica con su User-Agent, sin sesión.
Doble lectura de la misma ficha, fila a fila: A = bloque visible (.merch-rate-card: tipo de compra + .merch-cat__rate); B = los <span class="merch-cat__rate">
del HTML en bruto. Deben coincidir en número y orden; además el máximo debe coincidir con la cabecera «hasta X%» y la ficha
debe titularse «<tienda> Cashback». Las tarifas en euros (p. ej. «16,00 €») no se usan. Sin tarifa en % no se genera fila.
Formato de salida: slug|nombre|variante|pct|nuevos(1/0)|tope|lecturaA|lecturaB   (el mismo que lee importar_*.py)
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
MAX_NUEVAS = 360


def get(url):
    r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9"})
    with urllib.request.urlopen(r, timeout=30) as f:
        return f.status, f.read().decode("utf-8", "replace")


def num(s):
    return float(s.replace("%", "").replace(",", ".").strip())


data = json.loads((base / "cashback.json").read_text(encoding="utf-8"))
publicado = {}
for t in data["tiendas"]:
    for f in t["filas"]:
        if f["plataforma"] == "TopCashback":
            publicado.setdefault(t["slug"], []).append(f["pct"])
cand = [t for t in data["tiendas"] if len({f["plataforma"] for f in t["filas"]}) >= 2]
cand.sort(key=lambda t: (-len({f["plataforma"] for f in t["filas"]}), -len(t["filas"])))
slugs = list(publicado) + [t["slug"] for t in cand if t["slug"] not in publicado][:MAX_NUEVAS]
if "--prueba" in sys.argv:
    slugs = slugs[:12]
print(len(slugs), "fichas a leer")

cambios, vistos, errores = [], set(), 0
for i, s in enumerate(slugs, 1):
    try:
        st, t = get(f"https://www.topcashback.es/{s}/")
        if st == 200:
            soup = BeautifulSoup(t, "html.parser")
            texto = re.sub(r"\s+", " ", soup.get_text(" "))
            cab = re.search(r"Consigue un reembolso de hasta\s*(?:hasta\s*)?(\d+(?:[.,]\d+)?)\s*%\s*por tu compra", texto)
            tarjetas = []
            titulo_ok = False
            for c in soup.select(".merch-rate-card"):
                h2 = c.select_one(".merch-cat__title")
                subs, rates = c.select(".merch-cat__sub-cat"), c.select(".merch-cat__rate")
                if h2 and subs and len(subs) == len(rates):
                    htxt = re.sub(r"\s+", " ", h2.get_text()).strip()
                    titulo_ok = bool(re.match(r".+ Cashback$", htxt))
                    for sub, rate in zip(subs, rates):
                        if re.fullmatch(r"\d+(?:[.,]\d+)?\s*%", rate.get_text().strip()):
                            tarjetas.append((re.sub(r"\s+", " ", sub.get_text()).strip(), rate.get_text().strip(), htxt))
            crudo = re.findall(r'<span class="merch-cat__rate">\s*(\d+(?:[.,]\d+)?\s*%)\s*</span>', t)
            if cab and tarjetas and titulo_ok and [r for _, r, _ in tarjetas] == [c.strip() for c in crudo]                     and max(num(r) for _, r, _ in tarjetas) == num(cab.group(1)):
                vistos.add(s)
                pos = [x for x in tarjetas if num(x[1]) > 0]
                if not pos and s in publicado:
                    vistos.discard(s)
                nombre = re.sub(r" Cashback$", "", tarjetas[0][2]).replace("|", "/")
                if pos and sorted(num(x[1]) for x in pos) != sorted(publicado.get(s, [])):
                    for sub, r, h2t in pos:
                        nuevos = 1 if re.search(r"nuev", sub, re.I) else 0
                        cambios.append("|".join([s, nombre, sub.replace("|", "/"), f"{num(r):g}", str(nuevos), "",
                                                 f"Bloque de la ficha: {sub} {r}",
                                                 f"HTML de la ficha: {r} (cabecera: hasta {cab.group(1)}%)"]))
    except Exception as e:  # ficha no leída: cuenta como fallo si estaba publicada
        errores += 1
        if errores <= 3:
            print("error en", s, type(e).__name__, e, flush=True)
    if i % 50 == 0:
        print(i, "/", len(slugs), flush=True)
    time.sleep(PAUSA)

fallos = [s for s in publicado if s not in vistos]
(base / "cambios_topcashback.txt").write_text("\n".join(cambios) + "\n", encoding="utf-8")
(base / "fallos_topcashback.txt").write_text("\n".join(fallos) + "\n", encoding="utf-8")
print(f"listo: {len(cambios)} tarifas en cambios, {len(vistos)} fichas leídas bien, {len(fallos)} fallos, {errores} errores de red")
