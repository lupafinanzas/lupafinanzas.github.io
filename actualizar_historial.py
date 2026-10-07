"""Guarda el histórico del cashback: solo anota un punto cuando la tarifa cambia (o cuando aparece por primera vez).

Uso: python actualizar_historial.py   (después de los importadores y antes de generar las páginas)
Archivo: datos/historial.json -> {"desde": "AAAA-MM-DD", "series": {"slug|plataforma|variante": [["AAAA-MM-DD", pct], ...]}}
Con esto las fichas de tienda pueden mostrar la evolución de cada tarifa y cuándo suelen subir. Es un dato propio: solo existe desde que se guarda.
"""
import datetime
import json
import pathlib

from util_rutas import datos

base = pathlib.Path(__file__).parent
hoy = datetime.date.today().isoformat()
ruta = datos("historial.json")
hist = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {"desde": hoy, "series": {}}
series = hist["series"]
data = json.loads((base / "cashback.json").read_text(encoding="utf-8"))
nuevos = cambios = 0
for t in data["tiendas"]:
    for f in t["filas"]:
        clave = f"{t['slug']}|{f['plataforma']}|{f.get('variante') or ''}"
        s = series.setdefault(clave, [])
        if not s:
            s.append([hoy, f["pct"]])
            nuevos += 1
        elif s[-1][1] != f["pct"]:
            if s[-1][0] == hoy:
                s[-1][1] = f["pct"]
            else:
                s.append([hoy, f["pct"]])
            cambios += 1
ruta.write_text(json.dumps(hist, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(f"histórico: {len(series)} series, {nuevos} nuevas, {cambios} cambios de tarifa hoy")
