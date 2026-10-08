"""Convierte la lectura de TopCashback (leer_topcashback.py) en filas de cashback.json.

Uso:  python importar_topcashback.py lectura_beruby.txt
Diario: python importar_topcashback.py cambios.txt --refrescar fallos.txt
Formato: slug|nombre|variante|pct|nuevos(1/0)|tope|lecturaA|lecturaB   (una línea por tarifa mayor que 0)
Todas las tarifas de una tienda se reemplazan juntas. Las tiendas se unen por slug o nombre normalizado.
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


def quitar_tildes(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if not unicodedata.combining(c))


def norm(s):
    return re.sub(r"[^a-z0-9]", "", quitar_tildes(s))


def slugify(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", quitar_tildes(s))).strip("-")


por_slug = {t["slug"]: t for t in data["tiendas"]}
por_nombre = {norm(t["nombre"]): t for t in data["tiendas"]}
lectura = {}
for linea in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if linea.strip() and linea.count("|") == 7:
        s, nom, var, pct, nue, tope, a, b = linea.split("|")
        lectura.setdefault(s, {"nombre": nom, "filas": []})["filas"].append(
            dict(variante=var, pct=float(pct), nuevos=nue == "1", tope=float(tope) if tope else None, a=a, b=b))

nuevas, descartadas, retiradas = 0, [], 0
for bs, r in sorted(lectura.items()):
    if any(not 0 < x["pct"] <= 100 for x in r["filas"]):
        descartadas.append(bs)
        continue
    t = por_slug.get(bs)  # solo tiendas que ya existen (se piden por nuestro slug); no se crean tiendas nuevas
    if t is None:
        descartadas.append(bs)
        continue
    filas = []
    for x in r["filas"]:
        f = {"plataforma": "TopCashback", "pct": x["pct"], "hasta_pct": False, "habitual_pct": x["pct"], "tipo": "habitual",
             "tope": x["tope"], "primera_compra": False, "detalle": "Tarifa de la ficha de TopCashback: " + x["variante"],
             "fin": None, "fuente": f"https://www.topcashback.es/{bs}/", "leido": hoy, "doble_lectura": True,
             "lecturas": [x["a"], x["b"]]}
        if len(r["filas"]) > 1 or x["nuevos"]:
            f["variante"] = x["variante"][:60]
        if x["nuevos"]:
            f["solo_clientes_nuevos"] = True
            f["tipo"] = "bienvenida"
            f.pop("habitual_pct")
        filas.append(f)
    t["filas"] = [f for f in t["filas"] if f["plataforma"] != "TopCashback"] + filas
    nuevas += 1

if "--refrescar" in sys.argv:
    fallos = {s.strip() for s in pathlib.Path(sys.argv[sys.argv.index("--refrescar") + 1]).read_text(encoding="utf-8").splitlines() if s.strip()}
    total = len({f["fuente"] for t in data["tiendas"] for f in t["filas"] if f["plataforma"] == "TopCashback"})
    if total and len(fallos) > 0.3 * total:
        sys.exit(f"Demasiados fallos ({len(fallos)} de {total}): la lectura no es fiable, no se toca cashback.json")
    for t in data["tiendas"]:
        nf = []
        for f in t["filas"]:
            if f["plataforma"] == "TopCashback":
                bs = f["fuente"].rstrip("/").rsplit("/", 1)[-1]
                if bs not in lectura:
                    if bs in fallos:
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
    f.write(f"\n## TopCashback {hoy}: {nuevas} tiendas añadidas o cambiadas, {retiradas} filas retiradas, {len(descartadas)} descartadas\n")
print(f"{nuevas} tiendas añadidas o cambiadas, {retiradas} filas retiradas, {len(descartadas)} descartadas")
