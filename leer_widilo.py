"""Lector de Widilo en Python (sin navegador). Equivale a lector_widilo.js y escribe directamente los archivos de los importadores.

Uso: python leer_widilo.py            (lee ~900 fichas; unos 30 minutos con la pausa de 2 s)
     python leer_widilo.py --prueba   (solo 25 fichas)
Salida en esta carpeta:
  cambios_widilo.txt  -> slug|nombre|pct|subida(1/0)|habitual   (fichas nuevas o con cifra distinta; doble lectura superada)
  fallos_widilo.txt   -> slugs publicados cuya ficha ya no cumple la doble lectura
  descuentos_widilo.txt -> slug|tienda|valor|codigo/oferta|código|caduca|modificado|título|acumulable(1/0)
Después: python importar_widilo.py cambios_widilo.txt --refrescar fallos_widilo.txt  y  python importar_descuentos.py descuentos_widilo.txt
Doble lectura del cashback: (A) título o meta descripción de la ficha ("3,9% Cashback") y (B) los datos de la ficha (bloque ng-state).
Respeta robots.txt de Widilo, se identifica con su propio User-Agent y no usa sesión ni credenciales.
"""
import datetime
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
RE_CASHBACK = re.compile(r"(\d+(?:,\d+)?)\s?%\s*(?:de\s*)?cashback", re.I)
hoy = datetime.date.today()


def get(url):
    r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9"})
    with urllib.request.urlopen(r, timeout=30) as f:
        return f.status, f.read().decode("utf-8", "replace")


def num(s):
    return float(str(s).replace("%", "").replace(",", ".").strip())


def buscar_ficha(x, ruta="", prof=0):
    """Localiza en el ng-state el objeto de la ficha de la tienda (no las similares)."""
    if prof > 9 or x is None:
        return None
    if isinstance(x, str):
        if x.startswith("{") and len(x) > 50:
            try:
                return buscar_ficha(json.loads(x), ruta + "~", prof + 1)
            except ValueError:
                return None
        return None
    if isinstance(x, list):
        for i, v in enumerate(x):
            r = buscar_ficha(v, f"{ruta}.{i}", prof + 1)
            if r:
                return r
        return None
    if isinstance(x, dict):
        if "cashbackRate" in x and "metaTitle" in x and not re.search(r"similarShops|\.shops\.", ruta):
            return x
        for k, v in x.items():
            r = buscar_ficha(v, f"{ruta}.{k}", prof + 1)
            if r:
                return r
    return None


publicado = {}
data = json.loads((base / "cashback.json").read_text(encoding="utf-8"))
for t in data["tiendas"]:
    for f in t["filas"]:
        if f["plataforma"] == "Widilo":
            publicado[f["fuente"].rstrip("/").split("/")[-1]] = f

_, sm = get("https://www.widilo.es/shop-sitemap.xml")
slugs = re.findall(r"<loc>https://www\.widilo\.es/codigo-descuento/([a-z0-9-]+)</loc>", sm)
if "--prueba" in sys.argv:
    slugs = slugs[:25]
print(len(slugs), "fichas a leer")

cambios, descuentos, vistos, errores = [], [], set(), 0
for i, s in enumerate(slugs, 1):
    try:
        st, t = get("https://www.widilo.es/codigo-descuento/" + s)
        if st == 200:
            soup = BeautifulSoup(t, "html.parser")
            el = soup.find("script", id="ng-state")
            main = buscar_ficha(json.loads(el.string)) if el and el.string else None
            deals = (main or {}).get("deals") or []
            nombre_t = (deals[0].get("shopName") if deals else None) or s
            for dl in deals:
                mod = str(dl.get("modificationDate") or "")[:10]
                try:
                    hace = (hoy - datetime.date.fromisoformat(mod)).days
                except ValueError:
                    continue
                exp = str(dl.get("expirationDate") or "")[:10]
                try:
                    vigente = bool(exp) and not dl.get("isExpired") and datetime.date.fromisoformat(exp) >= hoy
                except ValueError:
                    vigente = False
                if dl.get("isExpired") or dl.get("isSignUpNewsletter") or dl.get("privateVoucher") or (not vigente and not hace <= 14):
                    continue
                limpia = lambda v: re.sub(r"\s+", " ", str(v or "")).strip().replace("|", "/")
                es_cod = bool(dl.get("isCoupon"))
                descuentos.append("|".join([s, limpia(nombre_t), limpia(dl.get("dealValue")), "codigo" if es_cod else "oferta",
                                            limpia(dl.get("coupon")) if es_cod else "", exp, mod, limpia(dl.get("title")),
                                            "0" if dl.get("isNotCumulative") else "1"]))
            a = RE_CASHBACK.search(soup.title.get_text() if soup.title else "")
            if not a:
                meta = soup.find("meta", attrs={"name": "description"})
                a = RE_CASHBACK.search(meta.get("content", "") if meta else "")
            if (main and a and main.get("isCashback") is True and main.get("cashbackType") == 1 and not main.get("hasMultipleCashbackValue")
                    and 0 < main.get("cashbackRate", 0) <= 100 and num(a.group(1)) == main["cashbackRate"]):
                nombre = re.sub(r"\s+", " ", nombre_t).strip().replace("|", "/")
                if nombre:
                    vistos.add(s)
                    inc = 1 if main.get("cashbackIsIncrease") and main.get("cashbackBeforeIncreaseValue") else 0
                    hab = num(main["cashbackBeforeIncreaseValue"]) if inc else main["cashbackRate"]
                    p = publicado.get(s)
                    if not p or p["pct"] != main["cashbackRate"] or (1 if p["tipo"] == "aumentado" else 0) != inc:
                        cambios.append(f"{s}|{nombre}|{main['cashbackRate']:g}|{inc}|{hab:g}")
    except Exception as e:
        errores += 1
        if errores <= 3:
            print("error en", s, type(e).__name__, e, flush=True)
    if i % 100 == 0:
        print(i, "/", len(slugs), flush=True)
    time.sleep(PAUSA)

fallos = [s for s in publicado if s not in vistos]
(base / "cambios_widilo.txt").write_text("\n".join(cambios) + "\n", encoding="utf-8")
(base / "fallos_widilo.txt").write_text("\n".join(fallos) + "\n", encoding="utf-8")
(base / "descuentos_widilo.txt").write_text("\n".join(sorted(descuentos)) + "\n", encoding="utf-8")
print(f"listo: {len(cambios)} cambios de cashback, {len(fallos)} fallos, {len(descuentos)} ofertas con fecha, {errores} errores de red")
