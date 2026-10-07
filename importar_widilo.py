"""Convierte la lectura de Widilo (lector_widilo.js) en filas de cashback.json.

Uso:  python importar_widilo.py lectura_widilo.txt
Diario: python importar_widilo.py cambios.txt --refrescar fallos.txt
Formato de cada línea: slug|nombre|pct|subida(1/0)|habitual|lecturaA|lecturaB
Solo entran fichas que pasaron la doble lectura en el navegador (A = título/meta, B = datos de la ficha).
Las tiendas se unen a las existentes por slug o por nombre normalizado; las nuevas se crean.
"""
import datetime
from util_rutas import registro_cambios
import json
import pathlib
import re
import sys
import unicodedata

base = pathlib.Path(__file__).parent
hoy = datetime.date.today().isoformat()
data = json.loads((base / "cashback.json").read_text(encoding="utf-8"))


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if not unicodedata.combining(c)))


def slugify(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", "".join(c for c in unicodedata.normalize("NFD", s.lower()) if not unicodedata.combining(c)))).strip("-")


por_slug = {t["slug"]: t for t in data["tiendas"]}
por_nombre = {norm(t["nombre"]): t for t in data["tiendas"]}
lectura = {}
EXCLUIDAS = {"ria"}  # servicios financieros: fuera de este comparador
MAX_PCT = 50  # cifras mayores (p. ej. 100 %) suelen ser solo para clientes nuevos o primer pedido: revisión manual, no se publican


def es(n):
    return f"{n:g}".replace(".", ",")


revisar = []
for linea in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    n = linea.count("|")
    if not linea.strip() or n not in (4, 6):
        continue
    if n == 6:  # formato completo del lector: slug|nombre|pct|subida|habitual|lecturaA|lecturaB
        s, nom, pct, inc, hab, a, b = linea.split("|")
    else:  # formato compacto: slug|nombre|pct|subida|habitual (las dos lecturas ya se comprobaron en el navegador)
        s, nom, pct, inc, hab = linea.split("|")
        a = f"{es(float(pct))} % cashback (título o meta de la ficha)"
        b = f"{es(float(pct))} %" + (f" (antes {es(float(hab))} %)" if inc == "1" else "")
    if s in EXCLUIDAS:
        continue
    if float(pct) > MAX_PCT:
        revisar.append((s, pct))
        continue
    lectura[s] = dict(nombre=nom, pct=float(pct), inc=inc == "1", hab=float(hab), a=a, b=b)

nuevas, descartadas, retiradas = 0, [], 0
for ws, r in sorted(lectura.items()):
    if not 0 < r["pct"] <= 100 or (r["inc"] and r["hab"] >= r["pct"]):
        descartadas.append((ws, r["a"]))
        continue
    t = por_slug.get(ws) or por_nombre.get(norm(r["nombre"]))
    if t is None:
        slug = slugify(r["nombre"]) or ws
        if slug in por_slug:
            slug = ws
        t = {"slug": slug, "nombre": r["nombre"], "filas": []}
        data["tiendas"].append(t)
        por_slug[slug] = t
        por_nombre[norm(r["nombre"])] = t
    fila = {"plataforma": "Widilo", "pct": r["pct"], "hasta_pct": False, "habitual_pct": r["hab"],
            "tipo": "aumentado" if r["inc"] else "habitual", "tope": None, "primera_compra": False,
            "detalle": ("Subida de Widilo; no indica fecha de fin. " if r["inc"] else "") + "+ bono de bienvenida de Widilo al registrarte (ver condiciones en la ficha).",
            "fin": None, "fuente": f"https://www.widilo.es/codigo-descuento/{ws}", "leido": hoy, "doble_lectura": True,
            "lecturas": [f"Título/meta de la ficha: {r['a']}", f"Datos de la ficha: cashback {r['b']}"]}
    t["filas"] = [f for f in t["filas"] if f["plataforma"] != "Widilo"] + [fila]
    nuevas += 1

if "--refrescar" in sys.argv:
    fallos = {s.strip() for s in pathlib.Path(sys.argv[sys.argv.index("--refrescar") + 1]).read_text(encoding="utf-8").splitlines() if s.strip()}
    total = sum(1 for t in data["tiendas"] for f in t["filas"] if f["plataforma"] == "Widilo")
    if total and len(fallos) > 0.15 * total:
        sys.exit(f"Demasiados fallos ({len(fallos)} de {total}): la lectura no es fiable, no se toca cashback.json")
    cambiados = set(lectura)
    for t in data["tiendas"]:
        nf = []
        for f in t["filas"]:
            if f["plataforma"] == "Widilo":
                ws = f["fuente"].rsplit("/", 1)[-1]
                if ws not in cambiados:
                    if ws in fallos:
                        retiradas += 1
                        continue
                    f["leido"] = hoy
            nf.append(f)
        t["filas"] = nf
    data["tiendas"] = [t for t in data["tiendas"] if t["filas"]]
    data["actualizado"] = hoy

data["tiendas"].sort(key=lambda t: t["nombre"].lower())
(base / "cashback.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
with (registro_cambios()).open("a", encoding="utf-8") as f:
    f.write(f"\n## Widilo {hoy}: {nuevas} filas añadidas o cambiadas, {retiradas} retiradas, {len(descartadas)} descartadas\n")
if revisar:
    with (registro_cambios()).open("a", encoding="utf-8") as f:
        f.write("Widilo: no publicadas por superar el 50 % (revisar a mano; suelen ser solo para clientes nuevos): " + ", ".join(f"{a} {b} %" for a, b in revisar) + "\n")
print(f"{nuevas} filas añadidas o cambiadas, {retiradas} retiradas, {len(descartadas)} descartadas, {len(revisar)} a revisar")
