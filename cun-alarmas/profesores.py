"""
profesores.py
--------------
Lee la lista de profesores (nombre + correo) desde un archivo Excel.
Por defecto lee data/profesores.xlsx del repo; si el usuario sube uno
nuevo desde la app, se usa ese en su lugar (solo para esa sesión, no
se sobreescribe el del repo -- para que quede permanente hay que
reemplazar el archivo en GitHub).
"""

from pathlib import Path
import pandas as pd

DEFAULT_PATH = Path(__file__).parent / "data" / "profesores.xlsx"

COLUMNAS_ESPERADAS = ["nombre", "correo"]


def leer_profesores(file_like_or_path) -> pd.DataFrame:
    df = pd.read_excel(file_like_or_path)
    df.columns = [c.strip().lower() for c in df.columns]
    faltantes = [c for c in COLUMNAS_ESPERADAS if c not in df.columns]
    if faltantes:
        raise ValueError(
            f"Al Excel le faltan las columnas {faltantes}. "
            f"Debe tener columnas 'nombre' y 'correo'."
        )
    df = df.dropna(subset=["correo"]).copy()
    df["nombre"] = df["nombre"].fillna("").astype(str).str.strip()
    df["correo"] = df["correo"].astype(str).str.strip()
    return df[COLUMNAS_ESPERADAS]


def cargar_profesores_por_defecto() -> pd.DataFrame:
    if DEFAULT_PATH.exists():
        return leer_profesores(DEFAULT_PATH)
    return pd.DataFrame(columns=COLUMNAS_ESPERADAS)
