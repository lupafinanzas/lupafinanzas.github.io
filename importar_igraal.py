"""Convierte la lectura de iGraal (leer_igraal.py) en filas de cashback.json.

Uso:  python importar_igraal.py cambios_igraal.txt
Diario: python importar_igraal.py cambios_igraal.txt --refrescar fallos_igraal.txt
Formato: slug|pct|hasta(1/0)|habitual|fin(d/m/aaaa)|lecturaA|lecturaB   (una línea por tienda con triple lectura coincidente)
Solo toca tiendas que ya existen en cashback.json (se unen por slug) y reemplaza su fila de iGraal.
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

lectura = {}
for linea in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if linea.strip() and linea.count("|") == 6:
        s, pct, hasta, hab, fin, a, b = linea.split("|")
        lectura[s] = dict(pct=float(pct), hasta=hasta == "1", hab=float(hab) if hab else None, fin=fin, a=a, b=b)

nuevas, descartadas, retiradas = 0, [], 0
for s, r in sorted(lectura.items()):
    t = por_slug.get(s)
    if t is None or not 0 < r["pct"] <= 100:
        descartadas.append(s)
        continue
    fin = None
    if r["fin"]:
        d, m, y = r["fin"].split("/")
        fin = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    aumentado = r["hab"] is not None and r["hab"] < r["pct"]
    f = {"plataforma": "iGraal", "pct": r["pct"], "hasta_pct": r["hasta"], "habitual_pct": r["hab"] if aumentado else r["pct"],
         "tipo": "aumentado" if aumentado else "habitual", "tope": None, "primera_compra": False,
         "detalle": "Subida temporal de iGraal" if aumentado else "Tarifa de la ficha de iGraal",
         "fin": fin, "fuente": f"https://es.igraal.com/codigos-promocionales/{s}", "leido": hoy, "doble_lectura": True,
         "lecturas": [r["a"], r["b"]]}
    previa = next((x for x in t["filas"] if x["plataforma"] == "iGraal"), None)
    if previa and previa["pct"] == r["pct"] and bool(previa.get("hasta_pct")) == r["hasta"]:
        # misma tarifa que ya teníamos: se conserva (habitual y fin de una subida, leídos de otra tarjeta) y solo se renueva la fecha
        previa["leido"], previa["doble_lectura"] = hoy, True
        previa["lecturas"] = [r["a"], r["b"]]
        continue
    t["filas"] = [x for x in t["filas"] if x["plataforma"] != "iGraal"] + [f]
    nuevas += 1

if "--refrescar" in sys.argv:
    fallos = {s.strip() for s in pathlib.Path(sys.argv[sys.argv.index("--refrescar") + 1]).read_text(encoding="utf-8").splitlines() if s.strip()}
    total = len({f["fuente"] for t in data["tiendas"] for f in t["filas"] if f["plataforma"] == "iGraal"})
    if total and len(fallos) > 0.3 * total:
        sys.exit(f"Demasiados fallos ({len(fallos)} de {total}): la lectura no es fiable, no se toca cashback.json")
    for t in data["tiendas"]:
        nf = []
        for f in t["filas"]:
            if f["plataforma"] == "iGraal" and t["slug"] not in lectura:
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
    f.write(f"\n## iGraal {hoy}: {nuevas} tiendas añadidas o cambiadas, {retiradas} filas retiradas, {len(descartadas)} descartadas\n")
print(f"{nuevas} tiendas añadidas o cambiadas, {retiradas} filas retiradas, {len(descartadas)} descartadas")
