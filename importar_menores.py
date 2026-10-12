"""Aplica a cashback.json la lectura de Letyshops, Klarna y Consupermiso (leer_menores.py).

Uso: python importar_menores.py lectura_menores.json
Solo renueva o corrige filas que YA existen de esas plataformas; no crea tiendas ni filas nuevas (las redacta a mano la tarea del PC).

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

from util_rutas import registro_cambios

base = pathlib.Path(__file__).parent
hoy = datetime.date.today().isoformat()
data = json.loads((base / "cashback.json").read_text(encoding="utf-8"))
lectura = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
RE_LETY = re.compile(r"https://letyshops\.com/es/shops/([a-z0-9-]+)$")
# cómo se llama la tienda en la dirección de la plataforma cuando no coincide con nuestro slug
ALIAS = {"Klarna": {}, "Consupermiso": {}}


def clave(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def firma(r):
    texto = f"{r['pct']:g}|{'hasta' if r['hasta'] else 'fijo'}|" + ";".join(f"{p:g} {t}" for p, t in r["conds"])
    return f"{len(r['conds'])}-" + hashlib.sha1(texto.encode("utf-8")).hexdigest()[:12]  # nº de líneas de condiciones + resumen


renovadas, cambiadas, revisar, sin_lectura = 0, [], [], []

for t in data["tiendas"]:
    for f in t["filas"]:
        plataforma = f["plataforma"]
        nombre = f"{t['nombre']} / {plataforma}" + (f" ({f['variante']})" if f.get("variante") else "")
        if plataforma in ("Klarna", "Consupermiso"):
            if not lectura["paginas_ok"].get(plataforma):
                sin_lectura.append(nombre)
                continue
            porclave = {clave(k): v for k, v in lectura[plataforma].items()}
            r = porclave.get(clave(f.get("clave_fuente") or ALIAS[plataforma].get(t["slug"], t["slug"])))
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
