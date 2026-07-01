import json
import shutil
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from local_crm.analytics_bridge import run_analysis
from local_crm.config import EXPEDIENTES_ROOT
from local_crm.db import connect, init_db, rows_to_dicts


APP_DIR = Path(__file__).resolve().parent
app = FastAPI(title="CRM Farmacias Local")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")


@app.on_event("startup")
def startup() -> None:
    init_db()
    EXPEDIENTES_ROOT.mkdir(parents=True, exist_ok=True)


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("crm.html", {"request": request})


@app.get("/api/dashboard")
def dashboard() -> dict:
    with connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM farmacias").fetchone()[0]
        clientes = conn.execute("SELECT COUNT(*) FROM farmacias WHERE estado_contacto = 'Activa'").fetchone()[0]
        reuniones = conn.execute("SELECT COUNT(*) FROM farmacias WHERE reunion_agendada = 1").fetchone()[0]
        expedientes = conn.execute("SELECT COUNT(*) FROM expedientes").fetchone()[0]
        stages = rows_to_dicts(
            conn.execute(
                """
                SELECT etapa_pipeline AS etapa, COUNT(*) AS total
                FROM farmacias
                GROUP BY etapa_pipeline
                ORDER BY etapa_pipeline
                """
            ).fetchall()
        )
    return {"total": total, "clientes": clientes, "reuniones": reuniones, "expedientes": expedientes, "stages": stages}


@app.get("/api/farmacias")
def farmacias(q: str = "", provincia: str = "", estado: str = "") -> list[dict]:
    sql = "SELECT * FROM farmacias WHERE 1=1"
    params: dict[str, str] = {}
    if q:
        sql += " AND (nombre_comercial LIKE :q OR municipio LIKE :q OR localidad LIKE :q)"
        params["q"] = f"%{q}%"
    if provincia:
        sql += " AND provincia = :provincia"
        params["provincia"] = provincia
    if estado:
        sql += " AND estado_contacto = :estado"
        params["estado"] = estado
    sql += " ORDER BY provincia, municipio, nombre_comercial LIMIT 5000"
    with connect() as conn:
        return rows_to_dicts(conn.execute(sql, params).fetchall())


@app.get("/api/farmacias/{farmacia_id}")
def farmacia_detail(farmacia_id: int) -> dict:
    with connect() as conn:
        farmacia = conn.execute("SELECT * FROM farmacias WHERE id = ?", (farmacia_id,)).fetchone()
        if not farmacia:
            raise HTTPException(status_code=404, detail="Farmacia no encontrada")
        expedientes = rows_to_dicts(conn.execute("SELECT * FROM expedientes WHERE farmacia_id = ? ORDER BY id DESC", (farmacia_id,)).fetchall())
    return {"farmacia": dict(farmacia), "expedientes": expedientes}


@app.post("/api/farmacias/{farmacia_id}/estado")
def update_estado(farmacia_id: int, estado_contacto: str = Form(...), etapa_pipeline: int = Form(...), reunion_agendada: int = Form(0)) -> dict:
    with connect() as conn:
        conn.execute(
            """
            UPDATE farmacias
            SET estado_contacto = ?, etapa_pipeline = ?, reunion_agendada = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (estado_contacto, etapa_pipeline, reunion_agendada, farmacia_id),
        )
        conn.commit()
    return {"ok": True}


@app.get("/api/expedientes")
def list_expedientes(farmacia_id: int | None = None) -> list[dict]:
    with connect() as conn:
        if farmacia_id:
            rows = conn.execute("SELECT * FROM expedientes WHERE farmacia_id = ? ORDER BY id DESC", (farmacia_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM expedientes ORDER BY id DESC").fetchall()
    return rows_to_dicts(rows)


@app.post("/api/expedientes")
def create_expediente(farmacia_id: int = Form(...), titulo: str = Form(...), tipo: str = Form("Auditoria"), descripcion: str = Form("")) -> dict:
    folder = EXPEDIENTES_ROOT / f"farmacia_{farmacia_id}" / titulo.strip().replace(" ", "_")
    folder.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO expedientes (farmacia_id, titulo, tipo, carpeta_path, descripcion)
            VALUES (?, ?, ?, ?, ?)
            """,
            (farmacia_id, titulo, tipo, str(folder), descripcion),
        )
        conn.commit()
        expediente_id = cur.lastrowid
    return {"id": expediente_id, "carpeta_path": str(folder)}


@app.post("/api/expedientes/{expediente_id}/documentos")
def upload_document(expediente_id: int, file: UploadFile = File(...)) -> dict:
    with connect() as conn:
        expediente = conn.execute("SELECT * FROM expedientes WHERE id = ?", (expediente_id,)).fetchone()
        if not expediente:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        folder = Path(expediente["carpeta_path"])
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / file.filename
        with target.open("wb") as fh:
            shutil.copyfileobj(file.file, fh)
        conn.execute(
            "INSERT INTO expediente_documentos (expediente_id, filename, file_path, content_type) VALUES (?, ?, ?, ?)",
            (expediente_id, file.filename, str(target), file.content_type),
        )
        conn.commit()
    return {"filename": file.filename, "file_path": str(target)}


@app.post("/api/expedientes/{expediente_id}/generar-auditoria")
def generar_auditoria(expediente_id: int) -> dict:
    with connect() as conn:
        expediente = conn.execute("SELECT * FROM expedientes WHERE id = ?", (expediente_id,)).fetchone()
        if not expediente:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")
        result = run_analysis(expediente_id, Path(expediente["carpeta_path"]))
        conn.execute(
            """
            INSERT INTO analisis_resultados (expediente_id, status, resumen, payload_json, output_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                expediente_id,
                str(result.get("status", "ok")),
                str(result.get("resumen", "")),
                json.dumps(result, ensure_ascii=False),
                str(result.get("output_path", "")),
            ),
        )
        conn.execute("UPDATE expedientes SET estado = 'En curso', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (expediente_id,))
        conn.commit()
    return result
