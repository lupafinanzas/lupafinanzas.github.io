"""Aplica a cashback.json la lectura de Letyshops, Klarna y Consupermiso (leer_menores.py).

Uso: python importar_menores.py lectura_menores.json
De Letyshops solo renueva o corrige filas que YA existen (las redacta a mano la tarea del PC). De Klarna y Consupermiso, además, añade
las tiendas nuevas que aparezcan en su página: a la tienda del comparador con el mismo nombre o, si no existe, creando la tienda.

- Klarna y Consupermiso (una cifra por tienda): si la doble lectura coincide, se actualiza la cifra y la fecha. Si la tienda ya no
  aparece en la página, la fila no se renueva y la purga la retira a los 3 días.
- Letyshops (fichas con condiciones escritas a mano): cada fila guarda una «firma» de lo leído (cabecera + líneas de condiciones).
  · Firma igual que la última vez: se renueva la fecha (y el plazo de confirmación, si ha cambiado).
  · Ficha sencilla, sin líneas de condiciones ni antes ni ahora: se actualiza la cifra.
  · Cualquier otro cambio (categorías, cliente nuevo/existente…): NO se toca ni se renueva la fila y se apunta en el registro como
    «revisar a mano», para que no aparezca como de hoy un texto que ya no coincide con la ficha.
"""
import datetime
import hashlib
import json
import pathlib
import re
import sys
import unicodedata

from util_rutas import registro_cambios

base = pathlib.Path(__file__).parent
hoy = datetime.date.today().isoformat()
data = json.loads((base / "cashback.json").read_text(encoding="utf-8"))
lectura = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
RE_LETY = re.compile(r"https://letyshops\.com/es/shops/([a-z0-9-]+)$")
# cómo se llama la tienda en la dirección de la plataforma cuando no coincide con nuestro slug
ALIAS = {"Klarna": {}, "Consupermiso": {"tienda-real-madrid": "realmadrid", "atida-mifarma": "mifarma"}}
URL = {"Klarna": "https://www.klarna.com/es/cashback/", "Consupermiso": "https://www.consupermiso.com/ofertas-cashback"}
DETALLE = {"Klarna": "Solo si compras desde la app de Klarna", "Consupermiso": "Porcentaje máximo anunciado en su listado"}


def clave(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def slugify(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", "".join(x for x in unicodedata.normalize("NFD", s.lower()) if not unicodedata.combining(x)))).strip("-")


def firma(r):
    texto = f"{r['pct']:g}|{'hasta' if r['hasta'] else 'fijo'}|" + ";".join(f"{p:g} {t}" for p, t in r["conds"])
    return f"{len(r['conds'])}-" + hashlib.sha1(texto.encode("utf-8")).hexdigest()[:12]  # nº de líneas de condiciones + resumen


renovadas, cambiadas, revisar, sin_lectura, usadas = 0, [], [], [], {"Klarna": set(), "Consupermiso": set()}

for t in data["tiendas"]:
    for f in t["filas"]:
        plataforma = f["plataforma"]
        nombre = f"{t['nombre']} / {plataforma}" + (f" ({f['variante']})" if f.get("variante") else "")
        if plataforma in ("Klarna", "Consupermiso"):
            if not lectura["paginas_ok"].get(plataforma):
                sin_lectura.append(nombre)
                continue
            porclave = {clave(k): v for k, v in lectura[plataforma].items()}
            k = clave(f.get("clave_fuente") or ALIAS[plataforma].get(t["slug"], t["slug"]))
            r = porclave.get(k)
            usadas[plataforma].add(k)
            if r is None or not 0 < r["pct"] <= 100:
                sin_lectura.append(nombre + " (ya no aparece en la página o su lectura no coincide)")
                continue
            if f["pct"] != r["pct"] or bool(f.get("hasta_pct")) != r["hasta"]:
                cambiadas.append(f"{nombre}: {'hasta ' if f.get('hasta_pct') else ''}{f['pct']:g} % -> {'hasta ' if r['hasta'] else ''}{r['pct']:g} %")
                f["pct"], f["habitual_pct"], f["hasta_pct"] = r["pct"], r["pct"], r["hasta"]
            else:
                renovadas += 1
            f["leido"], f["doble_lectura"], f["lecturas"] = hoy, True, [r["a"], r["b"]]
        elif plataforma == "Letyshops":
            m = RE_LETY.match(f["fuente"])
            r = lectura["Letyshops"].get(m.group(1)) if m else None
            if r is None:
                sin_lectura.append(nombre)
                continue
            hoy_firma, pcts = firma(r), {p for p, _ in r["conds"]}
            sencilla = not f.get("categorias") and not f.get("variante") and not f.get("secundaria")
            if f.get("firma"):
                igual = f["firma"] == hoy_firma
                sin_conds_antes = f["firma"].startswith("0-")
            else:  # primera vez: la fila escrita a mano debe cuadrar con la ficha para darla por buena
                sin_conds_antes = sencilla and not r["conds"]
                if f.get("categorias"):
                    igual = {p for _, p in f["categorias"]} <= pcts and max(p for _, p in f["categorias"]) == r["pct"]
                elif f.get("secundaria"):
                    igual = f["pct"] in pcts
                else:
                    igual = f["pct"] == r["pct"] and (not r["conds"] or f["pct"] in pcts)
            if igual:
                renovadas += 1
            elif sencilla and sin_conds_antes and not r["conds"] and 0 < r["pct"] <= 100:
                cambiadas.append(f"{nombre}: {f['pct']:g} % -> {'hasta ' if r['hasta'] else ''}{r['pct']:g} %")
                f["pct"], f["habitual_pct"], f["hasta_pct"] = r["pct"], r["pct"], r["hasta"]
                f["lecturas"] = [r["a"], r["b"]]
            else:
                revisar.append(f"{nombre}: la ficha ha cambiado ({r['a']}; condiciones: " + ("; ".join(f"{p:g} % {x}" for p, x in r["conds"]) or "ninguna") + ")")
                continue
            if r["plazo"] and f.get("plazo_dias") != r["plazo"]:
                cambiadas.append(f"{nombre}: plazo de confirmación {f.get('plazo_dias')} -> {r['plazo']} días")
                f["plazo_dias"] = r["plazo"]
            f["firma"], f["leido"], f["doble_lectura"] = hoy_firma, hoy, True

# tiendas de Klarna y Consupermiso que todavía no tienen fila
por_clave = {}
for t in data["tiendas"]:
    por_clave.setdefault(clave(t["slug"]), t)
    por_clave.setdefault(clave(t["nombre"]), t)
for plataforma in ("Klarna", "Consupermiso"):
    if not lectura["paginas_ok"].get(plataforma):
        continue
    inverso = {clave(v): k for k, v in ALIAS[plataforma].items()}
    for s, r in sorted(lectura[plataforma].items()):
        if clave(s) in usadas[plataforma] or not 0 < r["pct"] <= 100:
            continue
        t = por_clave.get(clave(inverso[clave(s)])) if clave(s) in inverso else (por_clave.get(clave(s)) or por_clave.get(clave(r["nombre"])))
        if t is None:
            t = {"slug": slugify(r["nombre"]) or s, "nombre": r["nombre"], "filas": []}
            data["tiendas"].append(t)
            por_clave[clave(t["slug"])] = por_clave[clave(t["nombre"])] = t
        t["filas"].append({"plataforma": plataforma, "pct": r["pct"], "hasta_pct": r["hasta"], "habitual_pct": r["pct"], "tipo": "habitual", "tope": None,
                           "primera_compra": False, "detalle": DETALLE[plataforma], "fin": None, "fuente": URL[plataforma], "leido": hoy,
                           "doble_lectura": True, "lecturas": [r["a"], r["b"]], "clave_fuente": s})
        cambiadas.append(f"{t['nombre']} / {plataforma}: fila nueva, {'hasta ' if r['hasta'] else ''}{r['pct']:g} %")
data["tiendas"].sort(key=lambda t: t["nombre"].lower())

(base / "cashback.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
with registro_cambios().open("a", encoding="utf-8") as reg:
    reg.write(f"\n## Letyshops, Klarna y Consupermiso {hoy}: {renovadas} filas renovadas sin cambios, {len(cambiadas)} cambios, "
              f"{len(revisar)} por revisar a mano, {len(sin_lectura)} sin lectura\n")
    for linea in cambiadas:
        reg.write(f"- Cambio: {linea}\n")
    for linea in revisar:
        reg.write(f"- REVISAR A MANO: {linea}\n")
    for linea in sin_lectura:
        reg.write(f"- Sin lectura (no se renueva): {linea}\n")
print(f"{renovadas} filas renovadas, {len(cambiadas)} cambios, {len(revisar)} por revisar a mano, {len(sin_lectura)} sin lectura")
for linea in cambiadas + ["REVISAR: " + x for x in revisar] + ["SIN LECTURA: " + x for x in sin_lectura]:
    print(" -", linea)
