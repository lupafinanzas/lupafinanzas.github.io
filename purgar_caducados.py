"""Retira de cashback.json las filas cuya lectura es demasiado antigua o cuya oferta ya terminó.

Uso: python purgar_caducados.py [--dias 3]
Sirve para que, si una fuente deja de leerse unos días (por ejemplo mycashbacks, que solo se lee desde el navegador del usuario),
sus datos desaparezcan de la web en lugar de seguir apareciendo como si fueran de hoy. El validador exige lo mismo (máximo 3 días).
"""
import datetime
import json
import pathlib
import sys

from util_rutas import registro_cambios

base = pathlib.Path(__file__).parent
hoy = datetime.date.today()
max_dias = int(sys.argv[sys.argv.index("--dias") + 1]) if "--dias" in sys.argv else 3
data = json.loads((base / "cashback.json").read_text(encoding="utf-8"))
quitadas = {}
for t in data["tiendas"]:
    nuevas = []
    for f in t["filas"]:
        edad = (hoy - datetime.date.fromisoformat(f["leido"])).days
        termino = f.get("fin") and datetime.date.fromisoformat(f["fin"]) < hoy
        if edad > max_dias or termino:
            quitadas[f["plataforma"]] = quitadas.get(f["plataforma"], 0) + 1
        else:
            nuevas.append(f)
    t["filas"] = nuevas
data["tiendas"] = [t for t in data["tiendas"] if t["filas"]]
(base / "cashback.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
if quitadas:
    with registro_cambios().open("a", encoding="utf-8") as f:
        f.write(f"\n## Purga {hoy.isoformat()}: filas retiradas por antigüedad (>{max_dias} días) o fin de oferta: {quitadas}\n")
print("filas retiradas:", quitadas or "ninguna")
