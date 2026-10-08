"""Lector de iGraal en Python (sin navegador). Lee la ficha de cada tienda candidata y escribe las tarifas para importar_igraal.py.

Uso: python leer_igraal.py            (unas 360 fichas; ~12 minutos con la pausa de 2 s)
     python leer_igraal.py --prueba   (solo 12 fichas)
Salida: cambios_igraal.txt y fallos_igraal.txt en esta carpeta; después: python importar_igraal.py cambios_igraal.txt --refrescar fallos_igraal.txt
Fichas: https://es.igraal.com/codigos-promocionales/<slug> (su robots.txt lo permite). Se identifica con su User-Agent, no usa sesión.
Tiendas candidatas: las de cashback.json con 2 o más plataformas (las más buscadas primero) y todas las que ya tienen fila de iGraal.
Triple lectura de la misma ficha: A = título de la página («… + X % Cashback»), B = primer título de tarjeta («[Hasta] X % de cashback»),
C = texto «de cashback» del bloque destacado. Deben dar el mismo porcentaje; si no coinciden, no se toca la tienda.
Una subida temporal aparece como «hasta X % de cashback en lugar de Y %, hasta el dd/mm/aaaa» y se guarda como «aumentado».
"""
import json
import pathlib
import re
import sys
import time
import urllib.request

base = pathlib.Path(__file__).parent
UA = "LupaFinanzas-lector/1.0 (+https://lupafinanzas.github.io; lectura diaria de cashback)"
PAUSA = 2.0
MAX_NUEVAS = 360


def get(url):
    r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9"})
    with urllib.request.urlopen(r, timeout=30) as f:
        return f.status, f.read().decode("utf-8", "replace")


def limpia(s):
    return re.sub(r"\s+", " ", re.sub(r"[⁠-⁤​ ]", " ", s or "")).strip()


def num(s):
    return float(s.replace(",", "."))


data = json.loads((base / "cashback.json").read_text(encoding="utf-8"))
con_ig = {t["slug"] for t in data["tiendas"] if any(f["plataforma"] == "iGraal" for f in t["filas"])}
cand = [t for t in data["tiendas"] if len({f["plataforma"] for f in t["filas"]}) >= 2]
cand.sort(key=lambda t: (-len({f["plataforma"] for f in t["filas"]}), -len(t["filas"])))
slugs = list(con_ig) + [t["slug"] for t in cand if t["slug"] not in con_ig][:MAX_NUEVAS]
if "--prueba" in sys.argv:
    slugs = slugs[:12]
print(len(slugs), "fichas a leer")

RE_TARJETA = re.compile(r"^(Hasta )?([\d.,]+)\s*%\s*de cashback(?: en lugar de ([\d.,]+)\s*%(?:, hasta el (\d{1,2}/\d{1,2}/\d{4}))?)?$", re.I)
cambios, vistos, errores = [], set(), 0
for i, s in enumerate(slugs, 1):
    try:
        st, h = get(f"https://es.igraal.com/codigos-promocionales/{s}")
        if st == 200:
            titulo = limpia((re.search(r"<title>([^<]*)</title>", h) or [None, ""])[1])
            tarjetas = [limpia(m) for m in re.findall(r'id="offerbasecard-title"[^>]*>([^<]*)<', h)][:2]
            textos = [limpia(m) for m in re.findall(r'<span class="[^"]*">([^<]*de cashback[^<]*)</span>', h)][:2]
            a = re.search(r"\+\s*([\d.,]+)\s*%\s*Cashback", titulo)
            b = RE_TARJETA.match(tarjetas[0]) if tarjetas else None
            c = RE_TARJETA.match(textos[0]) if textos else None
            if a and b and c and num(a.group(1)) == num(b.group(2)) == num(c.group(2)) and bool(b.group(1)) == bool(c.group(1)):
                vistos.add(s)
                pct = num(b.group(2))
                if 0 < pct <= 100:
                    hasta = "1" if b.group(1) else "0"
                    habitual = f"{num(b.group(3)):g}" if b.group(3) else ""
                    fin = b.group(4) or ""
                    cambios.append("|".join([s, f"{pct:g}", hasta, habitual, fin, "Título de la ficha: " + titulo.replace("|", "/"),
                                             "Tarjeta de la oferta: " + tarjetas[0].replace("|", "/")]))
    except Exception as e:  # ficha no leída: cuenta como fallo si estaba publicada
        errores += 1
        if errores <= 3:
            print("error en", s, type(e).__name__, e, flush=True)
    if i % 50 == 0:
        print(i, "/", len(slugs), flush=True)
    time.sleep(PAUSA)

fallos = [s for s in con_ig if s not in vistos]
(base / "cambios_igraal.txt").write_text("\n".join(cambios) + "\n", encoding="utf-8")
(base / "fallos_igraal.txt").write_text("\n".join(fallos) + "\n", encoding="utf-8")
print(f"listo: {len(cambios)} tarifas, {len(vistos)} fichas con triple lectura, {len(fallos)} fallos, {errores} errores de red")
