import sqlite3
from pathlib import Path
from typing import Any

from local_crm.config import CRM_DB_PATH


SCHEMA = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS farmacias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_comercial TEXT NOT NULL,
    telefono TEXT,
    calle TEXT,
    provincia TEXT,
    localidad TEXT,
    municipio TEXT,
    codigo_postal TEXT,
    numero TEXT,
    estado_contacto TEXT NOT NULL DEFAULT 'Potencial',
    etapa_pipeline INTEGER NOT NULL DEFAULT 0,
    reunion_agendada INTEGER NOT NULL DEFAULT 0,
    fecha_ultimo_contacto TEXT,
    notas TEXT,
    kpi_facturacion REAL,
    kpi_margen REAL,
    kpi_ticket_medio REAL,
    kpi_ventas_mes REAL,
    kpi_alertas TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(nombre_comercial, municipio, provincia, telefono)
);

CREATE TABLE IF NOT EXISTS expedientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    farmacia_id INTEGER NOT NULL,
    titulo TEXT NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'Auditoria',
    estado TEXT NOT NULL DEFAULT 'Abierto',
    carpeta_path TEXT NOT NULL,
    descripcion TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(farmacia_id) REFERENCES farmacias(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS expediente_documentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expediente_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    content_type TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(expediente_id) REFERENCES expedientes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS analisis_resultados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expediente_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    resumen TEXT,
    payload_json TEXT,
    output_path TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(expediente_id) REFERENCES expedientes(id) ON DELETE CASCADE
);
"""


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or CRM_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | None = None) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]
