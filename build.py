"""Genera las redirecciones cortas (con contador GoatCounter: cada visita a /ir/<slug>/ cuenta como clic en la oferta) ir/<slug>/index.html a partir de promos.json.

Uso: python build.py   (ejecutar tras editar promos.json, antes de hacer commit)
Así los posts enlazan a  <web>/ir/<slug>/  y, si cambia el enlace de afiliado,
solo se edita promos.json y todos los posts antiguos siguen funcionando.
"""
import html
import json
import pathlib

base = pathlib.Path(__file__).parent
data = json.loads((base / "promos.json").read_text(encoding="utf-8"))

for p in data["promos"]:
    if not p.get("enlace"):
        continue
    url = html.escape(p["enlace"], quote=True)
    nombre = html.escape(p["nombre"])
    page = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<meta http-equiv="refresh" content="3; url={url}">
<title>Redirigiendo a {nombre}…</title></head>
<body style="font-family:system-ui,sans-serif;padding:2rem">
<p>Redirigiendo a {nombre}… (enlace de afiliado · Publicidad)</p>
<p>Si no ocurre nada, <a href="{url}" rel="noopener sponsored nofollow">pulsa aquí</a>.</p>
<script data-goatcounter="https://lupafinanzas.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
<script>setTimeout(function(){{location.replace({json.dumps(p["enlace"])});}},800);</script>
</body></html>
"""
    out = base / "ir" / p["slug"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    print("ok", p["slug"])
