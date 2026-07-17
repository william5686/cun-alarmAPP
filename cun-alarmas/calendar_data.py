"""
calendar_data.py
------------------
Carga calendars.json y ofrece funciones simples para que app.py
navegue: modalidad -> periodo -> unidad (corte/bloque) -> fecha.
"""

import json
from datetime import date
from pathlib import Path

DATA_PATH = Path(__file__).parent / "calendars.json"


def load_calendars() -> dict:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def periodos(modalidad: str, calendars: dict) -> list:
    """Lista de códigos de periodo para 'presencial' o 'virtual', en orden."""
    return list(calendars[modalidad].keys())


def unidades(modalidad: str, periodo: str, calendars: dict) -> list:
    """Nombres de las unidades (Corte/Bloque) disponibles para ese periodo."""
    return list(calendars[modalidad][periodo]["unidades"].keys())


def etiqueta_unidad(modalidad: str) -> str:
    """Cómo se le llama a la subdivisión según la modalidad."""
    return "Corte" if modalidad == "presencial" else "Bloque"


def fecha_cierre(modalidad: str, periodo: str, unidad: str, calendars: dict) -> date:
    iso = calendars[modalidad][periodo]["unidades"][unidad]
    return date.fromisoformat(iso)


def fecha_cierre_periodo(modalidad: str, periodo: str, calendars: dict) -> tuple:
    p = calendars[modalidad][periodo]
    return date.fromisoformat(p["cierre_periodo_inicio"]), date.fromisoformat(p["cierre_periodo_fin"])
