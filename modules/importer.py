from pathlib import Path
from typing import BinaryIO

import pandas as pd

from modules.scoring import ESTADOS_COMERCIALES, aplicar_scoring


MASTER_SHEET_NAME = "Farmacias"
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
    "id_farmacia": "id_farmacia",
    "id": "id_farmacia",
    "farmacia": "nombre",
    "nombre farmacia": "nombre",
    "nombre_farmacia": "nombre",
    "nombre": "nombre",
    "localidad": "municipio",
    "ciudad": "municipio",
    "municipio": "municipio",
    "provincia": "provincia",
    "titular": "titular",
    "propietario": "titular",
    "dueno": "titular",
    "dueño": "titular",
    "telefono": "telefono",
    "teléfono": "telefono",
    "email": "email",
    "correo": "email",
    "estado": "estado_comercial",
    "fase": "estado_comercial",
    "estado del contacto": "estado_comercial",
    "estado_del_contacto": "estado_comercial",
    "estado del proceso": "estado_comercial",
    "estado_del_proceso": "estado_comercial",
    "ultimo contacto": "fecha_ultimo_contacto",
    "último contacto": "fecha_ultimo_contacto",
    "ultima interaccion": "fecha_ultimo_contacto",
    "última interacción": "fecha_ultimo_contacto",
    "ultima_interaccion": "fecha_ultimo_contacto",
    "proxima accion": "proxima_accion",
    "próxima acción": "proxima_accion",
    "proxima_accion": "proxima_accion",
    "notas": "observaciones",
    "observaciones": "observaciones",
    "resultado ultimo contacto": "observaciones",
    "resultado último contacto": "observaciones",
    "resultado ultimo cotacto": "observaciones",
    "resultado_ultimo_cotacto": "observaciones",
    "potencial": "potencial_comercial",
    "potencial_comercial": "potencial_comercial",
    "facturacion": "facturacion_estimada",
    "facturación": "facturacion_estimada",
    "facturacion_estimada": "facturacion_estimada",
    "rentabilidad": "rentabilidad_estimada",
    "rentabilidad_estimada": "rentabilidad_estimada",
    "edad": "edad_titular",
    "edad_titular": "edad_titular",
    "empleados": "empleados",
    "num empleados": "empleados",
    "n empleados": "empleados",
    "interes": "interes_compraventa",
    "interés compraventa": "interes_compraventa",
    "interes_compraventa": "interes_compraventa",
    "visitas": "visitas_realizadas",
    "visitas_realizadas": "visitas_realizadas",
    "auditorias": "auditorias_vendidas",
    "auditorías": "auditorias_vendidas",
    "auditorias_vendidas": "auditorias_vendidas",
}

ESTADO_ALIASES = {
    "no contactado": "No contactada",
    "no contactada": "No contactada",
    "contactado": "Contactada manual",
    "contactada": "Contactada manual",
    "contactada ia": "Contactada IA",
    "contactada manual": "Contactada manual",
    "interesado": "Interesada",
    "interesada": "Interesada",
    "reunion agendada": "Reunión agendada",
    "reunión agendada": "Reunión agendada",
    "auditoria propuesta": "Auditoría propuesta",
    "auditoría propuesta": "Auditoría propuesta",
    "auditoria vendida": "Auditoría vendida",
    "auditoría vendida": "Auditoría vendida",
    "cliente recurrente": "Cliente recurrente",
    "descartado": "Descartada",
    "descartada": "Descartada",
    "prospecto": "No contactada",
}


def normalize_column_name(column: object) -> str:
    clean = str(column).strip().lower().replace("\n", " ")
    clean = " ".join(clean.split())
    return COLUMN_ALIASES.get(clean, clean.replace(" ", "_"))


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = df.rename(columns={column: normalize_column_name(column) for column in df.columns})
    if not renamed.columns.duplicated().any():
        return renamed

    normalized = pd.DataFrame(index=renamed.index)
    for column in dict.fromkeys(renamed.columns):
        values = renamed.loc[:, renamed.columns == column]
        if values.shape[1] == 1:
            normalized[column] = values.iloc[:, 0]
        else:
            normalized[column] = values.bfill(axis=1).iloc[:, 0]
    return normalized


def validate_required_columns(df: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(missing)}")


def read_excel_sheet(source: str | Path | BinaryIO) -> tuple[pd.DataFrame, list[str]]:
    raw = pd.read_excel(source, sheet_name=MASTER_SHEET_NAME)
    raw = raw.dropna(how="all").copy()
    return raw, [str(column) for column in raw.columns]


def _slug(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.lower()
        .str.normalize("NFKD")
        .str.encode("ascii", errors="ignore")
        .str.decode("ascii")
        .str.replace(r"[^a-z0-9]+", "-", regex=True)
        .str.strip("-")
    )


def complete_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    completed = df.copy()
    if "nombre" not in completed.columns:
        validate_required_columns(completed)

    if "municipio" not in completed.columns:
        completed["municipio"] = ""
    if "provincia" not in completed.columns:
        completed["provincia"] = completed["municipio"]
    if "titular" not in completed.columns:
        completed["titular"] = completed["nombre"]
    if "id_farmacia" not in completed.columns:
        base = _slug(completed["nombre"] + "-" + completed["municipio"].astype(str))
        completed["id_farmacia"] = "far-" + base + "-" + (completed.index + 1).astype(str)

    completed["provincia"] = completed["provincia"].fillna("").astype(str).str.strip()
    completed.loc[completed["provincia"] == "", "provincia"] = completed["municipio"]
    completed["titular"] = completed["titular"].fillna("").astype(str).str.strip()
    completed.loc[completed["titular"] == "", "titular"] = completed["nombre"]
    return completed


def normalize_estado(value: object) -> str:
    clean = str(value).strip()
    if clean in ESTADOS_COMERCIALES:
        return clean
    return ESTADO_ALIASES.get(clean.lower(), "No contactada")


def load_farmacias_excel(source: str | Path | BinaryIO) -> tuple[pd.DataFrame, dict[str, object]]:
    raw, detected_columns = read_excel_sheet(source)
    df = complete_required_columns(normalize_columns(raw))
    validate_required_columns(df)

    for column in OPTIONAL_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    df = df[CRM_COLUMNS].copy()
    for column in ["id_farmacia", "nombre", "municipio", "provincia", "titular"]:
        df[column] = df[column].astype(str).str.strip()

    df = df[(df["id_farmacia"] != "") & (df["nombre"] != "")].copy()
    df["estado_comercial"] = df["estado_comercial"].apply(normalize_estado)
    df["interes_compraventa"] = df["interes_compraventa"].replace("", "Medio").fillna("Medio")
    df["fecha_ultimo_contacto"] = pd.to_datetime(df["fecha_ultimo_contacto"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["fecha_ultimo_contacto"] = df["fecha_ultimo_contacto"].fillna("")

    imported = aplicar_scoring(df)
    debug = {
        "sheet_name": MASTER_SHEET_NAME,
        "detected_columns": detected_columns,
        "excel_rows": int(len(raw)),
        "rows_with_content": int(len(imported)),
    }
    return imported, debug
