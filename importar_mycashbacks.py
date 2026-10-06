"""Convierte la lectura de fichas de mycashbacks en filas de cashback.json.

Uso: python importar_mycashbacks.py lectura_mycashbacks.txt
Diario: python importar_mycashbacks.py cambios.txt --refrescar fallos.txt   (salida de lector_mycashbacks.js)
Formato: una ficha por línea, "slug|título de la ficha|1 si es 'Hasta el X %' / 0 si cifra fija".
Solo entran en el archivo las fichas que, al leerlas, cumplían la doble lectura: la cifra del TÍTULO
coincidía con la del BLOQUE de cashback, la ficha existía (200, sin redirigir) y no era financiera.
El validador vuelve a comprobar cifra y fuente después.
"""
import datetime
import json
import pathlib
import re
import sys

base = pathlib.Path(__file__).parent
hoy = datetime.date.today().isoformat()
EXCLUIDAS = {"bitpanda", "coinbase", "ria"}  # servicios financieros: fuera de este comparador
lectura = {}
for linea in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if linea.strip():
        slug, title, hasta = linea.split("|")
        m = re.search(r"(\d+(?:,\d+)?)\s*%", title)
        if m and slug not in EXCLUIDAS:
            lectura[slug] = {"title": title, "b": m.group(1), "hasta": hasta == "1"}
data = json.loads((base / "cashback.json").read_text(encoding="utf-8"))
tiendas = {t["slug"]: t for t in data["tiendas"]}


def num(s):
    return float(s.replace(",", "."))


def nombre(title):
    n = re.split(r"\s+cash\s?backs?\b", title, flags=re.I)[0].strip()
    return n if 0 < len(n) < 60 else None


nuevas, descartadas = 0, []
for slug, r in sorted(lectura.items()):
    if not 0 < num(r["b"]) <= 100:
        descartadas.append((slug, r["title"], r["b"]))
        continue
    pct, hasta = num(r["b"]), bool(r["hasta"])
    fila = {"plataforma": "mycashbacks", "pct": pct, "hasta_pct": hasta}
    if not hasta:
        fila["habitual_pct"] = pct
    fila.update({
        "tipo": "habitual", "tope": None, "primera_compra": False,
        "detalle": "Se calcula sobre el importe neto (sin IVA, envío ni recargos). Pago automático desde 1 € confirmado.",
        "fin": None, "fuente": f"https://www.mycashbacks.com/es/{slug}/", "leido": hoy, "doble_lectura": True,
        "lecturas": [f"Título de la ficha: {r['title']}", f"Bloque de la ficha: {'Hasta el ' if hasta else 'CASHBACK '}{r['b']}%"],
    })
    t = tiendas.get(slug)
    if t is None:
        nom = nombre(r["title"])
        if not nom:
            descartadas.append((slug, r["title"], "sin nombre"))
            continue
        t = {"slug": slug, "nombre": nom, "filas": []}
        data["tiendas"].append(t)
        tiendas[slug] = t
    t["filas"] = [f for f in t["filas"] if f["plataforma"] != "mycashbacks"] + [fila]
    nuevas += 1

retiradas = 0
if "--refrescar" in sys.argv:
    # Modo diario: lo que no aparece en CAMBIOS se leyó hoy y sigue igual (se refresca "leido");
    # lo que aparece en FALLOS ya no cumple la doble lectura y se retira.
    fallos = {s.strip() for s in pathlib.Path(sys.argv[sys.argv.index("--refrescar") + 1]).read_text(encoding="utf-8").splitlines() if s.strip()}
    total = sum(1 for t in data["tiendas"] for f in t["filas"] if f["plataforma"] == "mycashbacks")
    if total and len(fallos) > 0.15 * total:
        sys.exit(f"Demasiados fallos ({len(fallos)} de {total}): la lectura no es fiable, no se toca cashback.json")
    for t in data["tiendas"]:
        nuevas_filas = []
        for f in t["filas"]:
            if f["plataforma"] == "mycashbacks" and t["slug"] not in lectura:
                if t["slug"] in fallos:
                    retiradas += 1
                    continue
                f["leido"] = hoy
            nuevas_filas.append(f)
        t["filas"] = nuevas_filas
    data["tiendas"] = [t for t in data["tiendas"] if t["filas"]]
    data["actualizado"] = hoy

data["tiendas"].sort(key=lambda t: t["nombre"].lower())
(base / "cashback.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
log = base.parent / "cashback_cambios.md"
with log.open("a", encoding="utf-8") as f:
    f.write(f"\n## mycashbacks {hoy}: {nuevas} filas añadidas, {len(descartadas)} fichas descartadas (no cuadran las dos lecturas o no existen)\n")
    for s, t, b in descartadas[:200]:
        f.write(f"- {s}: «{t}» / bloque {b}\n")
print(f"{nuevas} filas añadidas o cambiadas, {retiradas} retiradas, {len(descartadas)} descartadas")
