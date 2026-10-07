"""Convierte la lectura de descuentos de Widilo (window.__descuentos de lector_widilo.js) en web/descuentos.json.

Uso: python importar_descuentos.py descuentos_widilo.txt
Cada línea: slug|tienda|valor|codigo/oferta|código|caduca|modificado|título|acumulable(1/0)
Reglas: solo ofertas con fecha de fin vigente o modificadas hace 14 días o menos; nada caducado; sin textos copiados
de la fuente más allá del título de la oferta y su importe; siempre con enlace a la fuente. El resultado de una prueba
en carrito se guarda en ../descuentos_verificaciones.json y se aplica en cada ejecución; una oferta con verificacion.estado == "no_funciona" se retira.
Estados de verificación: "verificado" (el carrito aplicó el descuento), "no_funciona" (se elimina), "no_verificable"
(no se pudo probar: se publica así, con la fecha). Sin campo "verificacion" = visto en la fuente, sin probar en la tienda.
"""
import datetime
import hashlib
import json
import pathlib
import sys

base = pathlib.Path(__file__).parent
hoy = datetime.date.today()
destino = base / "descuentos.json"
# Resultados de las pruebas en carrito (se guardan fuera de web/): {id: {estado, fecha, nota, ...}}
verif = {}
vpath = base.parent / "descuentos_verificaciones.json"
if vpath.exists():
    verif = json.loads(vpath.read_text(encoding="utf-8"))
previo = {}
if destino.exists():
    for d in json.loads(destino.read_text(encoding="utf-8")).get("descuentos", []):
        previo[d["id"]] = d

out, descartadas = [], 0
vistos = set()
for linea in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if linea.count("|") != 8:
        continue
    slug, tienda, valor, tipo, codigo, caduca, modif, titulo, acum = linea.split("|")
    if not titulo or not valor:
        descartadas += 1
        continue
    try:
        fin = datetime.date.fromisoformat(caduca) if caduca else None
        mod = datetime.date.fromisoformat(modif)
    except ValueError:
        descartadas += 1
        continue
    if fin and fin < hoy:
        descartadas += 1
        continue
    if not fin and (hoy - mod).days > 14:
        descartadas += 1
        continue
    did = hashlib.sha1(f"{slug}|{codigo}|{titulo}".encode("utf-8")).hexdigest()[:12]
    if did in vistos:
        continue
    vistos.add(did)
    d = {"id": did, "slug": slug, "tienda": tienda, "valor": valor, "tipo": tipo, "codigo": codigo or None,
         "caduca": caduca or None, "modificado_en_fuente": modif, "titulo": titulo, "acumulable": acum == "1",
         "fuente": f"https://www.widilo.es/codigo-descuento/{slug}", "leido": hoy.isoformat()}
    v = verif.get(did) or previo.get(did, {}).get("verificacion")
    if v:
        if v.get("estado") == "no_funciona":
            descartadas += 1
            continue
        d["verificacion"] = {k: v[k] for k in ("estado", "fecha", "nota") if k in v}
    out.append(d)

out.sort(key=lambda d: (d["caduca"] or "9999-12-31", d["tienda"].lower()))
destino.write_text(json.dumps({"actualizado": hoy.isoformat(), "descuentos": out}, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(out)} descuentos publicables, {descartadas} descartados")
