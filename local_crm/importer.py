from pathlib import Path

import pandas as pd

from local_crm.db import connect, init_db


COLUMN_MAP = {
    "NOMBRE_COMERCIAL": "nombre_comercial",
    "TELEFONO": "telefono",
    "CALLE": "calle",
    "PROVINCIA": "provincia",
    "LOCALIDAD": "localidad",
    "MUNICIPIO": "municipio",
    "CODIGO_POSTAL": "codigo_postal",
    "NUMERO": "numero",
}


def clean_phone(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def load_excel(excel_path: Path) -> pd.DataFrame:
    df = pd.read_excel(excel_path, sheet_name=0)
    df = df.rename(columns=COLUMN_MAP)
    missing = [column for column in COLUMN_MAP.values() if column not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas esperadas en el Excel: {', '.join(missing)}")

    df = df[list(COLUMN_MAP.values())].dropna(how="all").copy()
    df["nombre_comercial"] = df["nombre_comercial"].fillna("").astype(str).str.strip()
    df = df[df["nombre_comercial"] != ""].copy()
    df["telefono"] = df["telefono"].apply(clean_phone)
    for column in ["calle", "provincia", "localidad", "municipio", "codigo_postal", "numero"]:
        df[column] = df[column].fillna("").astype(str).str.strip()
        df[column] = df[column].str.replace(r"\.0$", "", regex=True)
    return df


def import_farmacias(excel_path: Path, reset: bool = False) -> int:
    init_db()
    df = load_excel(excel_path)
    with connect() as conn:
        if reset:
            conn.execute("DELETE FROM farmacias")
        conn.executemany(
            """
            INSERT INTO farmacias (
                nombre_comercial, telefono, calle, provincia, localidad,
                municipio, codigo_postal, numero, estado_contacto, etapa_pipeline
            )
            VALUES (
                :nombre_comercial, :telefono, :calle, :provincia, :localidad,
                :municipio, :codigo_postal, :numero, 'Potencial', 0
            )
            ON CONFLICT(nombre_comercial, municipio, provincia, telefono) DO UPDATE SET
                calle = excluded.calle,
                localidad = excluded.localidad,
                codigo_postal = excluded.codigo_postal,
                numero = excluded.numero,
                updated_at = CURRENT_TIMESTAMP;
            """,
            df.to_dict("records"),
        )
        conn.commit()
    return len(df)
