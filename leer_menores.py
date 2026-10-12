"""Lector de Letyshops, Klarna y Consupermiso en Python (sin navegador). Escribe lectura_menores.json para importar_menores.py.

Uso: python leer_menores.py     (unas 15 páginas; menos de 1 minuto con la pausa de 2 s)
Después: python importar_menores.py lectura_menores.json
Su robots.txt permite estas páginas al agente genérico. Se identifica con su User-Agent, no usa sesión.
Solo se releen las tiendas que ya tienen fila de estas plataformas en cashback.json (son pocas y están escritas a mano).

Doble lectura (dos sitios distintos de la misma página; si no coinciden, la tienda no se incluye):
- Letyshops, ficha https://letyshops.com/es/shops/<slug>: A = tarifa de la cabecera («[hasta] X % cashback»), B = frase del pie
  («Compra en … con cashback [hasta] X %»). Además se recogen las líneas de «Información y condiciones» y el plazo de confirmación.
- Klarna, https://www.klarna.com/es/cashback/: A = tarjeta visible («Tienda / X% de cashback»), B = dato incrustado de la misma tienda
  (cashbackDiscount.discountPercentage, en centésimas), unidos por el identificador de la tienda.
- Consupermiso, https://www.consupermiso.com/ofertas-cashback: A = sello de la tarjeta («X%»), B = frase («Gana hasta un X% de
  reembolso al comprar en …») y C = atributo title del enlace; las tres deben coincidir.
"""
import html
import json
import pathlib
import re
import time
import urllib.request

base = pathlib.Path(__file__).parent
UA = "LupaFinanzas-lector/1.0 (+https://lupafinanzas.github.io; lectura diaria de cashback)"
PAUSA = 2.0
URL_KLARNA = "https://www.klarna.com/es/cashback/"
URL_CONSUPERMISO = "https://www.consupermiso.com/ofertas-cashback"
RE_LETY = re.compile(r"https://letyshops\.com/es/shops/([a-z0-9-]+)$")


def get(url):
    r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "es-ES,es;q=0.9"})
    with urllib.request.urlopen(r, timeout=40) as f:
        return f.status, f.read().decode("utf-8", "replace")


def limpia(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or "")).replace("\xa0", " ")).strip()


def num(s):
    return float(s.replace(",", "."))


def leer_letyshops(h):
    """Devuelve el dict de la ficha o None si las dos lecturas no coinciden."""
    nombre = re.search(r'<h1[^>]*>(.*?)</h1>', h, re.S)
    texto = limpia(re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S))
    a = re.search(r"LetyShops\.com › Tiendas › (.{1,60}?) (hasta )?([\d.,]+) % cashback", texto)
    b = re.search(r"Compra en (.{1,60}?) con cashback (hasta )?([\d.,]+) %", texto)
    if not (a and b) or num(a.group(3)) != num(b.group(3)):  # el pie dice siempre «hasta»: solo se compara la cifra
        return None
    conds = []
    bloque = re.search(r"Información y condiciones</div>(.*?)(?:border border-gray-300 rounded|$)", h, re.S)
    if bloque:
        for pct, txt in re.findall(r'font-bold">\s*([\d.,]+)\s*(?:&nbsp;|\xa0|\s)%\s*</span>\s*</div>\s*<div class="ml-2">(.*?)</div>', bloque.group(1), re.S):
            conds.append([num(pct), limpia(txt)])
    plazo = re.search(r"se confirma y acredita en (\d+)(?: - (\d+))? días", texto)
    return {"nombre": a.group(1).strip() or (limpia(nombre.group(1)) if nombre else ""), "pct": num(a.group(3)), "hasta": bool(a.group(2)),
            "conds": conds, "plazo": [int(plazo.group(1)), int(plazo.group(2) or plazo.group(1))] if plazo else None,
            "a": f"Cabecera de la ficha: {a.group(1).strip()} {a.group(2) or ''}{a.group(3)} % cashback",
            "b": f"Pie de la ficha: Compra en {b.group(1).strip()} con cashback {b.group(2) or ''}{b.group(3)} %"}


def leer_klarna(h):
    visibles = {}
    sin_estilos = re.sub(r"<style.*?</style>", "", h, flags=re.S)  # las primeras tarjetas llevan estilos incrustados entre el nombre y la cifra
    for uid, slug, nombre, pct in re.findall(
            r'href="/es/store/([0-9a-f-]{36})/([a-z0-9-]+)/[^"]*"[^>]*>\s*<span aria-label="[^"]*"[^>]*>.{0,900}?<div class="[^"]*">([^<]{1,60})</div><div class="[^"]*">([\d.,]+)\s?% de cashback</div>',
            sin_estilos, re.S):
        visibles[uid] = (slug, html.unescape(nombre), num(pct))
    datos = {}
    for uid, pct100, arriba in re.findall(
            r'"storeKrn":"krn:[^"]*:([0-9a-f-]{36})"(?:(?!"storeKrn").){0,6000}?"cashbackDiscount":\{"discountPercentage":(\d+),.{0,200}?"showUpToPrefix":(true|false)', h, re.S):
        datos.setdefault(uid, set()).add((int(pct100) / 100, arriba == "true"))
    out = {}
    for uid, (slug, nombre, pct) in visibles.items():
        d = datos.get(uid) or set()
        if d and {x[0] for x in d} == {pct}:
            arriba = any(x[1] for x in d)  # el dato incrustado distingue «Hasta X %»; la tarjeta no
            out[slug] = {"nombre": nombre, "pct": pct, "hasta": arriba,
                         "a": f"Tarjeta de la página: {nombre} {pct:g} % de cashback".replace(".", ","),
                         "b": f"Dato incrustado de la tienda: {'Hasta ' if arriba else ''}{pct:g} % cashback".replace(".", ",")}
    return out


def leer_consupermiso(h):
    out = {}
    for slug, titulo, sello, frase, nombre in re.findall(
            r'<a href="/oferta-cashback/([^"]+)" class="prv-cashback"\s*title="([^"]*)">.*?reward-badge">\s*([^<]*?)\s*</span>.*?prv-cashback__desc">\s*(.*?)<b>(.*?)</b>',
            h, re.S):
        a = re.fullmatch(r"([\d.,]+)\s?%", sello.strip())
        b = re.search(r"Gana hasta un ([\d.,]+)\s?% de reembolso al comprar en", limpia(frase))
        c = re.search(r"Gana hasta ([\d.,]+)\s?% de reembolso al comprar en", html.unescape(titulo))
        if a and b and c and num(a.group(1)) == num(b.group(1)) == num(c.group(1)):
            nombre = limpia(nombre)
            out[slug] = {"nombre": nombre, "pct": num(a.group(1)), "hasta": True,
                         "a": f"Listado: Gana hasta un {b.group(1)}% de reembolso al comprar en {nombre}",
                         "b": f"Sello de la tarjeta: {a.group(1)}%"}
    return out


data = json.loads((base / "cashback.json").read_text(encoding="utf-8"))
slugs_lety = sorted({m.group(1) for t in data["tiendas"] for f in t["filas"] if f["plataforma"] == "Letyshops" for m in [RE_LETY.match(f["fuente"])] if m})
res = {"Letyshops": {}, "Klarna": {}, "Consupermiso": {}, "paginas_ok": {"Letyshops": [], "Klarna": False, "Consupermiso": False}}

for s in slugs_lety:
    try:
        st, h = get(f"https://letyshops.com/es/shops/{s}")
        if st == 200:
            res["paginas_ok"]["Letyshops"].append(s)
            r = leer_letyshops(h)
            if r:
                res["Letyshops"][s] = r
    except Exception as e:
        print("error en Letyshops", s, type(e).__name__, e, flush=True)
    time.sleep(PAUSA)

for plataforma, url, lector in (("Klarna", URL_KLARNA, leer_klarna), ("Consupermiso", URL_CONSUPERMISO, leer_consupermiso)):
    try:
        st, h = get(url)
        if st == 200:
            res[plataforma] = lector(h)
            res["paginas_ok"][plataforma] = bool(res[plataforma])  # una página sin ninguna tarjeta legible no cuenta como leída
        if not res[plataforma]:  # diagnóstico: qué ha devuelto la página cuando no se reconoce ninguna tarjeta
            titulo = re.search(r"<title[^>]*>(.*?)</title>", h, re.S)
            print(f"{plataforma}: estado {st}, {len(h)} caracteres, título «{limpia(titulo.group(1))[:80] if titulo else ''}», "
                  f"{h.count('de cashback')} «de cashback», {h.count('storeKrn')} storeKrn, {h.count('/es/store/')} enlaces de tienda, "
                  f"{h.count('prv-cashback')} tarjetas prv-cashback", flush=True)
    except Exception as e:
        print("error en", plataforma, type(e).__name__, e, flush=True)
    time.sleep(PAUSA)

(base / "lectura_menores.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"listo: Letyshops {len(res['Letyshops'])}/{len(slugs_lety)} fichas con doble lectura, Klarna {len(res['Klarna'])} tiendas, Consupermiso {len(res['Consupermiso'])} tiendas")
