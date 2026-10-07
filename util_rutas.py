"""Rutas compartidas por los scripts, para que funcionen igual en el PC del usuario y en GitHub Actions.

- Registro de cambios: en el PC se sigue usando ../cashback_cambios.md (lo lee la tarea programada); en Actions se escribe en registro/.
- Datos internos (verificaciones de códigos, línea base): web/datos/ (dentro del repositorio, para que Actions los vea).
"""
import os
import pathlib

BASE = pathlib.Path(__file__).parent
EN_ACTIONS = bool(os.environ.get("GITHUB_ACTIONS"))


def registro_cambios():
    p = BASE / "registro" / "cashback_cambios.md"
    if not EN_ACTIONS and (BASE.parent / "cashback_cambios.md").exists():
        p = BASE.parent / "cashback_cambios.md"
    p.parent.mkdir(exist_ok=True)
    return p


def datos(nombre):
    d = BASE / "datos"
    d.mkdir(exist_ok=True)
    return d / nombre
