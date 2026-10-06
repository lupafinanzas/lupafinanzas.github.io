"""Valida web/cashback.json antes de publicarlo. Sale con código 1 si hay errores.

Uso: python validar_cashback.py
Comprobaciones: estructura, rangos, dominio de la fuente, caducidad de la fecha de
lectura, ofertas vencidas, que las DOS lecturas contengan la cifra, y que los cambios
bruscos frente a la versión anterior (git HEAD) vengan marcados como confirmados.
"""
import datetime
import json
import pathlib
import re
import subprocess
import sys
from urllib.parse import urlparse

base = pathlib.Path(__file__).parent
hoy = datetime.date.today()
MAX_EDAD_DIAS = 3
TIPOS = {"habitual", "aumentado", "bienvenida", "categoria"}
DOMINIOS = {
    "iGraal": "igraal.com", "TopCashback": "topcashback.es", "Klarna": "klarna.com",
    "Beruby": "beruby.com", "Consupermiso": "consupermiso.com", "Letyshops": "letyshops.com", "Widilo": "widilo.es", "mycashbacks": "mycashbacks.com",
}
errores, avisos = [], []


def numeros(texto):
    return {float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", texto)}


def fecha(s):
    try:
        return datetime.date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


data = json.loads((base / "cashback.json").read_text(encoding="utf-8"))
previo = {}
try:
    ant = subprocess.run(["git", "show", "HEAD:cashback.json"], cwd=base, capture_output=True, text=True, encoding="utf-8")
    if ant.returncode == 0:
        for t in json.loads(ant.stdout)["tiendas"]:
            for f in t["filas"]:
                previo[(t["slug"], f["plataforma"], f.get("variante"))] = f
except Exception:
    pass

for t in data["tiendas"]:
    for f in t["filas"]:
        n = f"{t['nombre']} / {f.get('plataforma')}" + (f" ({f['variante']})" if f.get("variante") else "")
        for campo in ("plataforma", "pct", "tipo", "fuente", "leido", "lecturas"):
            if campo not in f:
                errores.append(f"{n}: falta el campo '{campo}'")
        if errores and any(e.startswith(n) for e in errores):
            continue
        if not isinstance(f["pct"], (int, float)) or not 0 < f["pct"] <= 100:
            errores.append(f"{n}: porcentaje fuera de rango ({f['pct']})")
        if f["tipo"] not in TIPOS:
            errores.append(f"{n}: tipo desconocido '{f['tipo']}'")
        if f.get("tope") is not None and f["tope"] < 0:
            errores.append(f"{n}: tope negativo")
        hab = f.get("habitual_pct")
        if hab is not None and not 0 <= hab <= 100:
            errores.append(f"{n}: habitual_pct fuera de rango")
        if f["tipo"] == "aumentado" and (hab is None or hab >= f["pct"]):
            errores.append(f"{n}: una subida temporal necesita habitual_pct menor que pct")
        dom = DOMINIOS.get(f["plataforma"])
        host = urlparse(f["fuente"]).hostname or ""
        if dom is None:
            avisos.append(f"{n}: plataforma sin dominio conocido para comprobar la fuente")
        elif not host.endswith(dom):
            errores.append(f"{n}: la fuente ({host}) no pertenece a {dom}")
        pz = f.get("plazo_dias")
        if pz is not None and not (isinstance(pz, list) and len(pz) == 2 and 0 < pz[0] <= pz[1] <= 400):
            errores.append(f"{n}: plazo_dias debe ser [mínimo, máximo] en días")
        lei = fecha(f["leido"])
        if lei is None:
            errores.append(f"{n}: fecha de lectura inválida")
        elif (hoy - lei).days > MAX_EDAD_DIAS:
            errores.append(f"{n}: dato caducado (leído hace {(hoy - lei).days} días)")
        if f.get("fin"):
            fin = fecha(f["fin"])
            if fin is None:
                errores.append(f"{n}: fecha de fin inválida")
            elif fin < hoy:
                errores.append(f"{n}: la oferta terminó el {f['fin']}; hay que quitarla o actualizarla")
        # doble lectura: dos textos distintos y ambos con la cifra
        if f.get("doble_lectura") is not True or len(f["lecturas"]) != 2 or f["lecturas"][0] == f["lecturas"][1]:
            errores.append(f"{n}: necesita doble lectura con dos textos distintos")
        else:
            for i, lec in enumerate(f["lecturas"], 1):
                validas = {f["pct"]}
                if f["tipo"] == "categoria":
                    validas |= {float(c[1]) for c in f.get("categorias", [])}
                if not validas & numeros(lec):
                    errores.append(f"{n}: la lectura {i} no contiene ninguna de las cifras {sorted(validas)} -> '{lec}'")
        # cambios bruscos frente a la versión publicada
        p = previo.get((t["slug"], f["plataforma"], f.get("variante")))
        if p and abs(p["pct"] - f["pct"]) > max(10, p["pct"] * 0.5) and not f.get("cambio_confirmado"):
            errores.append(f"{n}: cambio brusco {p['pct']} -> {f['pct']}; marcar 'cambio_confirmado' tras revisarlo a mano")

if errores:
    print("ERRORES:")
    for e in errores:
        print(" -", e)
if avisos:
    print("AVISOS:")
    for a in avisos:
        print(" -", a)
if errores:
    sys.exit(1)
print("cashback.json válido")
