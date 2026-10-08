"""Convierte la lectura de BestPrice (lector_bestprice.js) en filas de cashback.json.

Uso:  python importar_bestprice.py lectura_bestprice.json
Diario: python importar_bestprice.py lectura_bestprice.json --refrescar
Entrada: {"salida": [[slug, base1, niveles1, base2, niveles2, titulo], ...], "fallos": [slug, ...]}
Cifra principal = «Hasta X%» (nivel de entrada). El nivel más alto del programa de fidelidad («Nivel Negro: Y%») va en el detalle:
nunca se usa como cifra para ordenar, porque solo la consigue quien llega a ese nivel.
Solo toca tiendas que ya existen en cashback.json (se unen por slug).
"""
import datetime
import json
import pathlib
import sys

from util_rutas import registro_cambios

base = pathlib.Path(__file__).parent
hoy = datetime.date.today().isoformat()
data = json.loads((base / "cashback.json").read_text(encoding="utf-8"))
por_slug = {t["slug"]: t for t in data["tiendas"]}
lec = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))


def num(s):
    return float(str(s).replace(",", "."))


def fmt(x):
    return f"{x:g}".replace(".", ",")


nuevas, descartadas, retiradas, vistos = 0, [], 0, set()
for slug, b1, n1, b2, n2, titulo in lec["salida"]:
    t = por_slug.get(slug)
    hasta = str(b1).startswith("h")
    b1, b2 = str(b1).lstrip("h"), str(b2).lstrip("h")
    if t is None or num(b1) != num(b2) or sorted(n1) != sorted(n2) or not 0 < num(b1) <= 100:
        descartadas.append(slug)
        continue
    vistos.add(slug)
    pct = num(b1)
    niveles = {n.split(":")[0]: num(n.split(":")[1]) for n in n1}
    nota = ("Hasta " if hasta else "") + f"{fmt(pct)} % en el nivel de entrada de BestPrice"
    if niveles:
        nota += "; " + ", ".join(f"nivel {k}: {fmt(v)} %" for k, v in niveles.items()) + " (solo al llegar a ese nivel de su programa de fidelidad)"
    f = {"plataforma": "BestPrice", "pct": pct, "hasta_pct": hasta, "habitual_pct": pct, "tipo": "habitual", "tope": None,
         "primera_compra": False, "detalle": nota, "fin": None, "fuente": f"https://bestprice.com/es-es/store/{slug}",
         "leido": hoy, "doble_lectura": True,
         "lecturas": [f"Carga 1 de la ficha: {b1}% cashback" + (" | " + " ".join(n1) if n1 else ""),
                      f"Carga 2 de la ficha: {b2}% cashback" + (" | " + " ".join(n2) if n2 else "")]}
    if niveles:
        f["niveles"] = niveles
    t["filas"] = [x for x in t["filas"] if x["plataforma"] != "BestPrice"] + [f]
    nuevas += 1

if "--refrescar" in sys.argv:
    fallos = set(lec.get("fallos", []))
    total = len({f["fuente"] for t in data["tiendas"] for f in t["filas"] if f["plataforma"] == "BestPrice"})
    if total and len(fallos) > 0.3 * total:
        sys.exit(f"Demasiados fallos ({len(fallos)} de {total}): la lectura no es fiable, no se toca cashback.json")
    for t in data["tiendas"]:
        nf = []
        for f in t["filas"]:
            if f["plataforma"] == "BestPrice" and t["slug"] not in vistos:
                if t["slug"] in fallos:
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
    f.write(f"\n## BestPrice {hoy}: {nuevas} tiendas añadidas o cambiadas, {retiradas} filas retiradas, {len(descartadas)} descartadas\n")
print(f"{nuevas} tiendas añadidas o cambiadas, {retiradas} filas retiradas, {len(descartadas)} descartadas")
