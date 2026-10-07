"""Valida web/promos.json antes de publicarlo. Sale con código 1 si hay errores.

Uso: python validar_promos.py
Reglas: campos obligatorios; las 'publicada' deben tener verificación de hace menos de 7 días; las añadidas
automáticamente (campo 'auto': true) necesitan al menos 2 fuentes distintas, una oficial, y 'nota' >= 6;
ningún enlace de una promo marcada 'no_publicable'; el enlace, si lo hay, debe aparecer en enlaces_referidos.md.
"""
import datetime
import json
import pathlib
import sys
from urllib.parse import urlparse

base = pathlib.Path(__file__).parent
hoy = datetime.date.today()
ESTADOS = {"publicada", "en_verificacion", "no_publicable", "caducada"}
OBLIG = ("slug", "nombre", "tipo", "recompensa", "requisitos", "estado")
errores = []
data = json.loads((base / "promos.json").read_text(encoding="utf-8"))
enlaces = ""
try:
    enlaces = (base.parent / "enlaces_referidos.md").read_text(encoding="utf-8")
except OSError:
    pass
vistos = set()
for p in data["promos"]:
    n = p.get("slug", "?")
    for c in OBLIG:
        if not p.get(c):
            errores.append(f"{n}: falta '{c}'")
    if p.get("slug") in vistos:
        errores.append(f"{n}: slug repetido")
    vistos.add(p.get("slug"))
    if p.get("estado") not in ESTADOS:
        errores.append(f"{n}: estado desconocido '{p.get('estado')}'")
    if p.get("estado") == "no_publicable" and p.get("enlace"):
        errores.append(f"{n}: promo no publicable con enlace")
    if p.get("estado") == "publicada":
        try:
            v = datetime.date.fromisoformat(p.get("verificado") or "")
            if (hoy - v).days > 7:
                errores.append(f"{n}: publicada pero verificada hace {(hoy - v).days} días")
        except ValueError:
            errores.append(f"{n}: publicada sin fecha de verificación válida")
    if p.get("enlace") and p["enlace"] not in enlaces:
        errores.append(f"{n}: el enlace no figura en enlaces_referidos.md")
    if p.get("auto"):
        fuentes = p.get("fuentes") or []
        if len({urlparse(u).netloc for u in fuentes}) < 2:
            errores.append(f"{n}: automática con menos de 2 fuentes de dominios distintos")
        if not any(u.startswith("https://") for u in fuentes) or not p.get("fuente_oficial"):
            errores.append(f"{n}: automática sin fuente oficial leída ('fuente_oficial')")
        if not isinstance(p.get("nota"), (int, float)) or p["nota"] < 6:
            errores.append(f"{n}: automática con Nota Real menor de 6 o sin nota")
if errores:
    print("ERRORES:")
    for e in errores:
        print(" -", e)
    sys.exit(1)
print("promos.json válido")
