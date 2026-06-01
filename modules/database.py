import sqlite3
from pathlib import Path

import pandas as pd

from modules.scoring import aplicar_scoring


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "crm_farmacias.db"


ALL_COLUMNS = [
    "id_farmacia",
    "nombre",
    "municipio",
    "provincia",
    "titular",
    "telefono",
    "email",
    "estado_comercial",
    "prioridad",
    "score_comercial",
    "score_compraventa",
    "accion_recomendada",
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


SCHEMA = """
CREATE TABLE IF NOT EXISTS farmacias (
    id_farmacia TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    municipio TEXT NOT NULL,
    provincia TEXT NOT NULL,
    titular TEXT NOT NULL,
    telefono TEXT,
    email TEXT,
    estado_comercial TEXT DEFAULT 'No contactada',
    prioridad TEXT DEFAULT 'C',
    score_comercial REAL DEFAULT 0,
    score_compraventa REAL DEFAULT 0,
    accion_recomendada TEXT,
    proxima_accion TEXT,
    fecha_ultimo_contacto TEXT,
    observaciones TEXT,
    potencial_comercial REAL DEFAULT 0,
    facturacion_estimada REAL DEFAULT 0,
    rentabilidad_estimada REAL DEFAULT 0,
    edad_titular INTEGER DEFAULT 0,
    empleados INTEGER DEFAULT 0,
    interes_compraventa TEXT DEFAULT 'Medio',
    visitas_realizadas INTEGER DEFAULT 0,
    auditorias_vendidas INTEGER DEFAULT 0,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _table_columns(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("PRAGMA table_info(farmacias)").fetchall()
    return {row["name"] for row in rows}


def init_db() -> None:
    with get_connection() as conn:
        existing_columns = _table_columns(conn)
        if existing_columns and "id_farmacia" not in existing_columns:
            conn.execute("ALTER TABLE farmacias RENAME TO farmacias_legacy")
            existing_columns = set()

        conn.execute(SCHEMA)
        for column in set(ALL_COLUMNS) - existing_columns:
            if existing_columns:
                conn.execute(f"ALTER TABLE farmacias ADD COLUMN {column} TEXT")
        conn.commit()


def fetch_farmacias() -> pd.DataFrame:
    init_db()
    with get_connection() as conn:
        return pd.read_sql_query("SELECT * FROM farmacias ORDER BY score_comercial DESC, nombre", conn)


def upsert_farmacias(df: pd.DataFrame) -> int:
    if df.empty:
        return 0

    init_db()
    records = df.reindex(columns=ALL_COLUMNS).fillna("").to_dict("records")
    placeholders = ", ".join(f":{column}" for column in ALL_COLUMNS)
    assignments = ", ".join(f"{column} = excluded.{column}" for column in ALL_COLUMNS if column != "id_farmacia")

    sql = f"""
    INSERT INTO farmacias ({", ".join(ALL_COLUMNS)}, updated_at)
    VALUES ({placeholders}, CURRENT_TIMESTAMP)
    ON CONFLICT(id_farmacia) DO UPDATE SET
        {assignments},
        updated_at = CURRENT_TIMESTAMP;
    """

    with get_connection() as conn:
        conn.executemany(sql, records)
        conn.commit()

    return len(records)


def update_farmacia_fields(id_farmacia: str, fields: dict[str, object]) -> None:
    allowed = {"estado_comercial", "proxima_accion", "fecha_ultimo_contacto", "observaciones"}
    updates = {key: value for key, value in fields.items() if key in allowed}
    if not updates:
        return

    with get_connection() as conn:
        row = conn.execute("SELECT * FROM farmacias WHERE id_farmacia = ?", (id_farmacia,)).fetchone()
        if row is None:
            return

        merged = dict(row)
        merged.update(updates)
        scored = aplicar_scoring(pd.DataFrame([merged])).iloc[0].to_dict()
        recalculated = {
            **updates,
            "prioridad": scored["prioridad"],
            "score_comercial": scored["score_comercial"],
            "score_compraventa": scored["score_compraventa"],
            "accion_recomendada": scored["accion_recomendada"],
            "id_farmacia": id_farmacia,
        }
        set_clause = ", ".join(f"{column} = :{column}" for column in recalculated if column != "id_farmacia")
        conn.execute(
            f"UPDATE farmacias SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id_farmacia = :id_farmacia",
            recalculated,
        )
        conn.commit()
