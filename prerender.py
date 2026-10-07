"""Escribe en el HTML el contenido que las páginas pintan con JavaScript, para que buscadores y asistentes de IA (que muchas veces no ejecutan JS) lo vean.

Uso: python prerender.py   (desde web/, después de actualizar los .json y antes del commit)
Rellena entre marcadores <!--PRE:xxx-->...<!--/PRE:xxx--> dentro de los contenedores que luego vacía el JavaScript de cada página:
  promociones.html -> #lista (promos publicadas, con condiciones y nota)
  descuentos.html  -> #listaDto (los primeros descuentos, con su fecha)
  cashback.html    -> #picks y #podio (lo mejor de hoy y las subidas)
  comparador.html  -> bloque de enlaces a las fichas de tienda
Misma lógica que el JavaScript (sin «hasta», 2+ plataformas, <40 % en destacados). No inventa nada: solo vuelca los datos.
"""
import datetime
import html
import json
import pathlib
import re

BASE = pathlib.Path(__file__).parent
esc = html.escape
hoy = datetime.date.today()
cb = json.loads((BASE / "cashback.json").read_text(encoding="utf-8"))
promos = json.loads((BASE / "promos.json").read_text(encoding="utf-8"))["promos"]
dtos = json.loads((BASE / "descuentos.json").read_text(encoding="utf-8")).get("descuentos", [])


def pc(n):
    return f"{n:g}".replace(".", ",") + " %"


def eur(n):
    return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def fmt(iso):
    a, m, d = iso.split("-")
    return f"{d}/{m}/{a}"


def dias(iso):
    return (datetime.date.fromisoformat(iso) - hoy).days


def gana(f, imp=50):
    v = imp * f["pct"] / 100
    return min(v, f["tope"]) if f.get("tope") is not None else v


def poner(archivo, clave, contenido, contenedor_re):
    """Sustituye el contenido del contenedor (reconocido por su apertura) por los marcadores con el contenido."""
    p = BASE / archivo
    s = p.read_text(encoding="utf-8")
    ini, fin = f"<!--PRE:{clave}-->", f"<!--/PRE:{clave}-->"
    bloque = ini + contenido + fin
    if ini in s:
        s = re.sub(re.escape(ini) + r".*?" + re.escape(fin), lambda m: bloque, s, count=1, flags=re.S)
    else:
        m = re.search(contenedor_re, s, flags=re.S)
        if not m:
            print("AVISO: no encuentro el contenedor", clave, "en", archivo)
            return
        s = s[:m.end(1)] + bloque + s[m.start(2):]
    p.write_text(s, encoding="utf-8")


# ---- promociones
vis = [p for p in promos if p["estado"] == "publicada" and not (p.get("caduca") and dias(p["caduca"]) < 0)]
out = []
for p in vis:
    nota = ""
    if p.get("nota"):
        tot = sum(p["nota"].values())
        razones = "".join(f"<li><b>{k.capitalize()} ({p['nota'][k]:g}/2,5):</b> {esc(v)}</li>" for k, v in (p.get("nota_razon") or {}).items())
        nota = f"<p class=\"det\">Nota Real: {tot:g} / 10 (cada criterio puntúa de 0 a 2,5){(' · ' + esc(p['nota_texto'])) if p.get('nota_texto') else ''}</p>" + (f"<details open><summary>Por qué esta nota</summary><ul>{razones}</ul></details>" if razones else "")
    else:
        nota = "<p class=\"det\">Nota Real sin calcular todavía.</p>"
    enlace = ""
    if p.get("aviso"):
        enlace += f'<p class="det aviso-p">{esc(p["aviso"])}</p>'
    if p.get("enlace"):
        enlace += f'<p><a class="btn verde" href="ir/{esc(p["slug"])}/" rel="noopener sponsored nofollow">{esc(p.get("boton") or ("Ir a " + p["nombre"] + " →"))}</a></p>'
    if p.get("fuente_oficial"):
        enlace += f'<p><a href="{esc(p["fuente_oficial"])}" rel="noopener nofollow">Ver condiciones oficiales</a></p>'
    out.append(f'<article class="card promo"><div class="cab"><h3>{esc(p["nombre"])}</h3><span class="sello">{esc(p["tipo"])}</span></div>'
               f'<div class="gana">{esc(p.get("gana_corto") or p["recompensa"])}</div><div class="det">{esc(p.get("gana_sub") or "")}</div>'
               f'<p class="cond">{esc(p["requisitos"])}</p>{nota}{enlace}'
               f'<p class="mini">{("Hasta el " + fmt(p["caduca"]) + " · ") if p.get("caduca") else ""}Comprobado el {fmt(p["verificado"])}</p></article>')
# (patrón simple: el contenedor #lista llega hasta el aviso de publicidad)
p = BASE / "promociones.html"
s = p.read_text(encoding="utf-8")
m = re.search(r'(<div class="promos" id="lista">)(.*?)(</div>\s*<div class="aviso">)', s, flags=re.S)
if m:
    s = s[:m.end(1)] + "<!--PRE:lista-->" + "".join(out) + "<!--/PRE:lista-->" + s[m.start(3):]
    p.write_text(s, encoding="utf-8")


def reemplazar(archivo, id_contenedor, clave, contenido):
    p = BASE / archivo
    s = p.read_text(encoding="utf-8")
    ini, fin = f"<!--PRE:{clave}-->", f"<!--/PRE:{clave}-->"
    if ini in s and fin in s:  # ya prerenderizado: reemplazo exacto entre marcadores (nunca acumula)
        i, j = s.index(ini), s.index(fin)
        p.write_text(s[:i] + ini + contenido + s[j:], encoding="utf-8")
        return
    patron = r'(<div[^>]*id="' + id_contenedor + r'"[^>]*>)(.*?)(</div>\s*(?:<div|<p|</section|<section|<footer))'
    m = re.search(patron, s, flags=re.S)
    if not m:
        print("AVISO: no encuentro #", id_contenedor, "en", archivo)
        return
    s = s[:m.end(1)] + f"<!--PRE:{clave}-->" + contenido + f"<!--/PRE:{clave}-->" + s[m.start(3):]
    p.write_text(s, encoding="utf-8")


# ---- descuentos (los 40 que antes caducan; el JS muestra hasta 60 y permite filtrar)
vig = [d for d in dtos if not d.get("caduca") or dias(d["caduca"]) >= 0][:40]
out = []
for d in vig:
    v = d.get("verificacion")
    estado = ("Verificado en la tienda el " + fmt(v["fecha"])) if v and v["estado"] == "verificado" else "Visto en la fuente, sin probar en la tienda"
    out.append(f'<article class="card dto"><div class="cab"><h3>{esc(d["tienda"])}</h3><span class="valor">{esc(d["valor"] or "")}</span></div>'
               f'<div class="tit">{esc(d["titulo"])}</div>' + (f'<div class="cod">Código: {esc(d["codigo"])}</div>' if d.get("codigo") else "") +
               f'<p class="mini">{"Hasta el " + fmt(d["caduca"]) if d.get("caduca") else "Sin fecha de fin"} · {estado} · <a href="{esc(d["fuente"])}" rel="noopener nofollow">Ver en Widilo</a></p></article>')
reemplazar("descuentos.html", "listaDto", "dto", "".join(out))

# ---- cashback: lo mejor de hoy y subidas
cand, subidas = {}, {}
for t in cb["tiendas"]:
    plats = {f["plataforma"] for f in t["filas"]}
    for f in t["filas"]:
        if f.get("fin") and dias(f["fin"]) < 0:
            continue
        nuevo = f.get("solo_clientes_nuevos") or f.get("primera_compra") or f["tipo"] == "bienvenida"
        if len(plats) >= 3 and not nuevo and not f.get("hasta_pct") and f["pct"] < 20:
            if t["slug"] not in cand or gana(f) > cand[t["slug"]][0]:
                cand[t["slug"]] = (gana(f), t, f)
        if f["tipo"] == "aumentado" and f.get("habitual_pct", 99) < f["pct"] and f["pct"] < 40 and not nuevo:
            if t["slug"] not in subidas or gana(f) > subidas[t["slug"]][0]:
                subidas[t["slug"]] = (gana(f), t, f)


def tarjeta(i, v, t, f, podio):
    extra = f' · antes {pc(f["habitual_pct"])}' if podio else ""
    fin = f' · {("Termina hoy" if dias(f["fin"]) == 0 else "Quedan " + str(dias(f["fin"])) + " días")}' if f.get("fin") else ""
    return (f'<a class="pick" href="comparador.html#{esc(t["slug"])}"><span class="puesto">{"Podio" if podio else "Nº"} {i}</span><h3>{esc(t["nombre"])}</h3>'
            f'<div class="gran">{pc(f["pct"]) if podio else eur(v)}<small>{("antes " + pc(f["habitual_pct"])) if podio else "con 50 €"}</small></div>'
            f'<div class="quien">con {esc(f["plataforma"])}{(" · " + eur(v) + " con 50 €") if podio else ""}{fin}</div></a>')


top = sorted(cand.values(), key=lambda x: -x[0])[:3]
reemplazar("cashback.html", "picks", "picks", "".join(tarjeta(i, *x, False) for i, x in enumerate(top, 1)))
ord_s = sorted(subidas.values(), key=lambda x: -x[0])
reemplazar("cashback.html", "podio", "podio", "".join(tarjeta(i, *x, True) for i, x in enumerate(ord_s[:3], 1)))
mas = "".join(f'<a class="sub1" href="comparador.html#{esc(t["slug"])}"><b>{esc(t["nombre"])}</b><span class="n">{pc(f["pct"])}</span><span class="q">{esc(f["plataforma"])} · antes {pc(f["habitual_pct"])}</span></a>' for v, t, f in ord_s[3:15])
reemplazar("cashback.html", "masSubidas", "mas", mas)

# ---- comparador: enlaces rastreables a las fichas de tienda
tiendas_dir = BASE / "tienda"
slugs = sorted(x.name for x in tiendas_dir.iterdir() if x.is_dir()) if tiendas_dir.exists() else []
nombres = {t["slug"]: t["nombre"] for t in cb["tiendas"]}
bloque = ('<nav class="seccion" aria-label="Fichas de tienda"><h2>Fichas por tienda</h2><p class="sub">Cashback comparado y descuentos vigentes en cada tienda.</p><div class="lista">'
          + "".join(f'<a href="tienda/{s}/">{esc(nombres.get(s, s))}</a>' for s in slugs[:400]) + '</div><p class="mini"><a href="tienda/">Ver todas las tiendas →</a></p></nav>')
p = BASE / "comparador.html"
s = p.read_text(encoding="utf-8")
ini, fin = "<!--PRE:tiendas-->", "<!--/PRE:tiendas-->"
if ini in s:
    s = re.sub(re.escape(ini) + r".*?" + re.escape(fin), lambda m: ini + bloque + fin, s, count=1, flags=re.S)
else:
    s = s.replace("  <footer class=\"pie\">", "  " + ini + bloque + fin + "\n  <footer class=\"pie\">", 1)
if "a.lista{" not in s and ".lista a" not in s:
    s = s.replace("</head>", "<style>.lista{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:8px;margin:12px 0}.lista a{display:block;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:9px 12px;text-decoration:none;font-size:.9rem}</style></head>", 1)
p.write_text(s, encoding="utf-8")
print("prerender listo:", len(vis), "promos,", len(vig), "descuentos,", len(top), "destacados,", len(ord_s), "subidas,", len(slugs), "enlaces a fichas")
