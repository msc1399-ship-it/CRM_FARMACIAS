from pathlib import Path

import pandas as pd
import streamlit as st

from modules.analytics import count_by, pipeline_summary, proximas_acciones, ranking_prioritarias
from modules.database import DB_PATH, count_farmacias, fetch_farmacias, init_db, reset_database, update_farmacia_fields, upsert_farmacias
from modules.importer import MASTER_SHEET_NAME, REQUIRED_COLUMNS, load_farmacias_excel
from modules.scoring import ESTADOS_COMERCIALES, aplicar_scoring, recomendar_accion


DATA_DIR = Path(__file__).parent / "data"
MASTER_XLSX = DATA_DIR / "farmacias_master.xlsx"

st.set_page_config(page_title="CRM Farmacias", layout="wide")


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    return fetch_farmacias()


def refresh_data() -> None:
    load_data.clear()


def import_master_excel(reset_before_import: bool = False) -> dict[str, object]:
    debug = {
        "excel_path": str(MASTER_XLSX.resolve()),
        "excel_exists": MASTER_XLSX.exists(),
        "sheet_name": MASTER_SHEET_NAME,
        "detected_columns": [],
        "excel_rows": 0,
        "rows_with_content": 0,
        "sqlite_total": count_farmacias(),
        "message": "",
    }

    if not MASTER_XLSX.exists():
        debug["message"] = "No se encontró data/farmacias_master.xlsx. Sube tu Excel real."
        return debug

    try:
        if reset_before_import:
            reset_database()

        df, import_debug = load_farmacias_excel(MASTER_XLSX)
        upsert_farmacias(df)
        refresh_data()
        debug.update(import_debug)
        debug["sqlite_total"] = count_farmacias()
        debug["message"] = f"Importadas o actualizadas {len(df)} farmacias desde el Excel real."
    except ValueError as exc:
        debug["message"] = str(exc)
    except Exception as exc:
        debug["message"] = f"No se pudo importar la hoja {MASTER_SHEET_NAME}: {exc}"

    return debug


def debug_view(debug: dict[str, object]) -> None:
    st.subheader("Depuración de importación")
    st.write(
        {
            "ruta_excel_usado": debug.get("excel_path", str(MASTER_XLSX.resolve())),
            "archivo_existe": debug.get("excel_exists", MASTER_XLSX.exists()),
            "hoja_leida": debug.get("sheet_name", MASTER_SHEET_NAME),
            "columnas_detectadas": debug.get("detected_columns", []),
            "filas_leidas_excel": debug.get("excel_rows", 0),
            "total_farmacias_sqlite": debug.get("sqlite_total", count_farmacias()),
        }
    )
    if debug.get("message"):
        st.info(str(debug["message"]))


def import_excel_view(debug: dict[str, object]) -> None:
    st.subheader("Importar Excel maestro")
    st.caption(f"Persistencia SQLite: {DB_PATH}")
    st.caption(f"Archivo principal: {MASTER_XLSX}")
    st.caption(f"Hoja obligatoria: {MASTER_SHEET_NAME}")
    st.write(f"Columnas obligatorias: {', '.join(REQUIRED_COLUMNS)}")

    if not MASTER_XLSX.exists():
        st.warning("No se encontró data/farmacias_master.xlsx. Sube tu Excel real.")

    uploaded_file = st.file_uploader("Subir Excel real como data/farmacias_master.xlsx", type=["xlsx", "xls"])
    if uploaded_file is not None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        MASTER_XLSX.write_bytes(uploaded_file.getbuffer())
        st.success("Excel real guardado en data/farmacias_master.xlsx.")

    if st.button("Importar Excel real", type="primary"):
        result = import_master_excel(reset_before_import=False)
        st.session_state["startup_import_debug"] = result
        debug = result
        if result.get("excel_exists"):
            st.success(str(result["message"]))
        else:
            st.warning(str(result["message"]))

    if st.button("Reiniciar base de datos e importar Excel real"):
        result = import_master_excel(reset_before_import=True)
        st.session_state["startup_import_debug"] = result
        debug = result
        if result.get("excel_exists"):
            st.success(str(result["message"]))
        else:
            st.warning(str(result["message"]))

    debug_view(debug)


def dashboard_view(df: pd.DataFrame) -> None:
    st.subheader("Dashboard general")
    if df.empty:
        st.info("Importa el Excel maestro para cargar el CRM.")
        return

    summary = pipeline_summary(df)
    cols = st.columns(5)
    cols[0].metric("Total farmacias", summary["total_farmacias"])
    cols[1].metric("Clientes activos", summary["clientes_activos"])
    cols[2].metric("Auditorías vendidas", summary["auditorias_vendidas"])
    cols[3].metric("Score comercial medio", f"{summary['score_comercial_medio']:.1f}")
    cols[4].metric("Score compraventa medio", f"{summary['score_compraventa_medio']:.1f}")

    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.write("Farmacias por fase del embudo")
        st.bar_chart(count_by(df, "estado_comercial", "estado").set_index("estado"))
    with chart_right:
        st.write("Farmacias por provincia")
        st.bar_chart(count_by(df, "provincia", "provincia").set_index("provincia"))

    table_left, table_right = st.columns(2)
    with table_left:
        st.write("Farmacias por prioridad")
        st.dataframe(count_by(df, "prioridad", "prioridad"), hide_index=True, use_container_width=True)
    with table_right:
        st.write("Farmacias por estado comercial")
        st.dataframe(count_by(df, "estado_comercial", "estado"), hide_index=True, use_container_width=True)

    st.write("Tabla de proximas acciones")
    st.dataframe(proximas_acciones(df), hide_index=True, use_container_width=True)

    st.write("Ranking de farmacias prioritarias")
    st.dataframe(ranking_prioritarias(df), hide_index=True, use_container_width=True)


def filter_table(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    search = st.text_input("Buscar por nombre, municipio, provincia o titular")
    c1, c2, c3, c4 = st.columns(4)
    estado = c1.multiselect("Estado comercial", ESTADOS_COMERCIALES)
    provincia = c2.multiselect("Provincia", sorted(data["provincia"].dropna().unique().tolist()))
    prioridad = c3.multiselect("Prioridad", ["A", "B", "C"])
    min_score = c4.slider("Score comercial minimo", 0, 100, 0)

    if search:
        mask = pd.Series(False, index=data.index)
        for column in ["nombre", "municipio", "provincia", "titular"]:
            mask = mask | data[column].astype(str).str.contains(search, case=False, na=False)
        data = data[mask]
    if estado:
        data = data[data["estado_comercial"].isin(estado)]
    if provincia:
        data = data[data["provincia"].isin(provincia)]
    if prioridad:
        data = data[data["prioridad"].isin(prioridad)]
    data = data[pd.to_numeric(data["score_comercial"], errors="coerce").fillna(0) >= min_score]
    return data


def table_view(df: pd.DataFrame) -> None:
    st.subheader("Vista tabla")
    if df.empty:
        st.info("Importa farmacias para usar la tabla.")
        return

    filtered = filter_table(df)
    editable_cols = [
        "id_farmacia",
        "nombre",
        "municipio",
        "provincia",
        "titular",
        "estado_comercial",
        "prioridad",
        "score_comercial",
        "score_compraventa",
        "proxima_accion",
        "fecha_ultimo_contacto",
        "observaciones",
    ]

    edited = st.data_editor(
        filtered[editable_cols],
        hide_index=True,
        use_container_width=True,
        disabled=[column for column in editable_cols if column not in {"estado_comercial", "proxima_accion", "fecha_ultimo_contacto", "observaciones"}],
        column_config={
            "estado_comercial": st.column_config.SelectboxColumn("estado_comercial", options=ESTADOS_COMERCIALES),
            "fecha_ultimo_contacto": st.column_config.TextColumn("fecha_ultimo_contacto", help="Formato recomendado: YYYY-MM-DD"),
        },
    )

    if st.button("Guardar ediciones"):
        original = filtered.set_index("id_farmacia")
        changes = 0
        for record in edited.to_dict("records"):
            id_farmacia = record["id_farmacia"]
            current = original.loc[id_farmacia]
            updates = {
                "estado_comercial": record["estado_comercial"],
                "proxima_accion": record["proxima_accion"],
                "fecha_ultimo_contacto": record["fecha_ultimo_contacto"],
                "observaciones": record["observaciones"],
            }
            if any(str(updates[key]) != str(current[key]) for key in updates):
                update_farmacia_fields(id_farmacia, updates)
                changes += 1
        refresh_data()
        st.success(f"{changes} fichas actualizadas.")


def farmacia_view(df: pd.DataFrame) -> None:
    st.subheader("Ficha de farmacia")
    if df.empty:
        st.info("Importa farmacias para consultar fichas.")
        return

    options = (df["nombre"] + " · " + df["municipio"] + " · " + df["id_farmacia"]).sort_values().tolist()
    selected = st.selectbox("Farmacia", options)
    id_farmacia = selected.split(" · ")[-1]
    account = df[df["id_farmacia"] == id_farmacia].iloc[0].copy()
    scored = aplicar_scoring(pd.DataFrame([account])).iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Score comercial", f"{scored['score_comercial']:.1f}")
    c2.metric("Score compraventa", f"{scored['score_compraventa']:.1f}")
    c3.metric("Prioridad", scored["prioridad"])
    st.info(recomendar_accion(scored))

    st.dataframe(pd.DataFrame(scored).reset_index().rename(columns={"index": "campo", 0: "valor"}), hide_index=True, use_container_width=True)


def main() -> None:
    init_db()
    if "startup_import_debug" not in st.session_state:
        st.session_state["startup_import_debug"] = import_master_excel(reset_before_import=True)

    startup_debug = st.session_state["startup_import_debug"]
    df = load_data()

    st.title("CRM Farmacias")
    st.caption("CRM interno para embudo comercial, scoring, compraventa y analítica de farmacias españolas.")

    dashboard, table, account, importer = st.tabs(["Dashboard", "Tabla", "Ficha", "Importar"])
    with dashboard:
        dashboard_view(df)
    with table:
        table_view(df)
    with account:
        farmacia_view(df)
    with importer:
        import_excel_view(startup_debug)


if __name__ == "__main__":
    main()
