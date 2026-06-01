from pathlib import Path
from typing import BinaryIO

import pandas as pd

from modules.scoring import ESTADOS_COMERCIALES, aplicar_scoring


REQUIRED_COLUMNS = ["id_farmacia", "nombre", "municipio", "provincia", "titular"]

OPTIONAL_COLUMNS = [
    "telefono",
    "email",
    "estado_comercial",
    "proxima_accion",
    "fecha_ultimo_contacto",
    "observaciones",
    "potencial_comercial",
    "facturacion_estimada",
    "rentabilidad_estimada",
    "edad_titular",
    "empleados",
    "interes_compraventa",
    "visitas_realizadas",
    "auditorias_vendidas",
]

CRM_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

COLUMN_ALIASES = {
    "id farmacia": "id_farmacia",
    "id": "id_farmacia",
    "farmacia": "nombre",
    "nombre farmacia": "nombre",
    "localidad": "municipio",
    "ciudad": "municipio",
    "propietario": "titular",
    "dueno": "titular",
    "dueño": "titular",
    "telefono": "telefono",
    "teléfono": "telefono",
    "correo": "email",
    "estado": "estado_comercial",
    "fase": "estado_comercial",
    "ultimo contacto": "fecha_ultimo_contacto",
    "último contacto": "fecha_ultimo_contacto",
    "notas": "observaciones",
    "potencial": "potencial_comercial",
    "facturacion": "facturacion_estimada",
    "facturación": "facturacion_estimada",
    "rentabilidad": "rentabilidad_estimada",
    "edad": "edad_titular",
    "num empleados": "empleados",
    "n empleados": "empleados",
    "interes": "interes_compraventa",
    "interés compraventa": "interes_compraventa",
    "visitas": "visitas_realizadas",
    "auditorias": "auditorias_vendidas",
    "auditorías": "auditorias_vendidas",
}


def normalize_column_name(column: object) -> str:
    clean = str(column).strip().lower().replace("\n", " ")
    clean = " ".join(clean.split())
    return COLUMN_ALIASES.get(clean, clean.replace(" ", "_"))


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={column: normalize_column_name(column) for column in df.columns})


def validate_required_columns(df: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(missing)}")


def load_farmacias_excel(source: str | Path | BinaryIO) -> pd.DataFrame:
    df = normalize_columns(pd.read_excel(source))
    validate_required_columns(df)

    for column in OPTIONAL_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    df = df[CRM_COLUMNS].copy()
    for column in ["id_farmacia", "nombre", "municipio", "provincia", "titular"]:
        df[column] = df[column].astype(str).str.strip()

    df = df[(df["id_farmacia"] != "") & (df["nombre"] != "")].copy()
    df["estado_comercial"] = df["estado_comercial"].replace("", "No contactada").fillna("No contactada")
    df.loc[~df["estado_comercial"].isin(ESTADOS_COMERCIALES), "estado_comercial"] = "No contactada"
    df["interes_compraventa"] = df["interes_compraventa"].replace("", "Medio").fillna("Medio")
    df["fecha_ultimo_contacto"] = pd.to_datetime(df["fecha_ultimo_contacto"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["fecha_ultimo_contacto"] = df["fecha_ultimo_contacto"].fillna("")

    return aplicar_scoring(df)
