from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.database import DB_PATH, count_farmacias, fetch_farmacias, init_db, reset_database, update_farmacia_fields, upsert_farmacias
from modules.importer import MASTER_SHEET_NAME, REQUIRED_COLUMNS, load_farmacias_excel
from modules.scoring import ESTADOS_COMERCIALES, aplicar_scoring, recomendar_accion


DATA_DIR = Path(__file__).parent / "data"
MASTER_XLSX = DATA_DIR / "farmacias_master.xlsx"

st.set_page_config(page_title="CRM Farmacias", layout="wide")

FUNNEL_STATES = [
    "No contactada",
    "Contactada",
    "Interesada",
    "Reunión agendada",
    "Auditoría propuesta",
    "Auditoría vendida",
    "Cliente recurrente",
]

SPAIN_PROVINCE_COORDS = {
    "A Coruna": (43.36, -8.41),
    "A Coruña": (43.36, -8.41),
    "Albacete": (38.99, -1.86),
    "Alicante": (38.35, -0.49),
    "Almeria": (36.84, -2.46),
    "Almería": (36.84, -2.46),
    "Asturias": (43.36, -5.85),
    "Avila": (40.66, -4.70),
    "Ávila": (40.66, -4.70),
    "Badajoz": (38.88, -6.97),
    "Barcelona": (41.39, 2.17),
    "Burgos": (42.34, -3.70),
    "Caceres": (39.48, -6.37),
    "Cáceres": (39.48, -6.37),
    "Cadiz": (36.52, -6.29),
    "Cádiz": (36.52, -6.29),
    "Cantabria": (43.46, -3.81),
    "Castellon": (39.99, -0.04),
    "Castellón": (39.99, -0.04),
    "Ciudad Real": (38.99, -3.93),
    "Cordoba": (37.88, -4.78),
    "Córdoba": (37.88, -4.78),
    "Cuenca": (40.07, -2.13),
    "Girona": (41.98, 2.82),
    "Granada": (37.18, -3.60),
    "Guadalajara": (40.63, -3.16),
    "Gipuzkoa": (43.32, -1.98),
    "Huelva": (37.26, -6.94),
    "Huesca": (42.14, -0.41),
    "Illes Balears": (39.57, 2.65),
    "Jaen": (37.78, -3.79),
    "Jaén": (37.78, -3.79),
    "La Rioja": (42.46, -2.45),
    "Las Palmas": (28.12, -15.43),
    "Leon": (42.60, -5.57),
    "León": (42.60, -5.57),
    "Lleida": (41.62, 0.62),
    "Lugo": (43.01, -7.56),
    "Madrid": (40.42, -3.70),
    "Malaga": (36.72, -4.42),
    "Málaga": (36.72, -4.42),
    "Murcia": (37.98, -1.13),
    "Navarra": (42.82, -1.64),
    "Ourense": (42.34, -7.86),
    "Palencia": (42.01, -4.53),
    "Pontevedra": (42.43, -8.64),
    "Salamanca": (40.97, -5.66),
    "Santa Cruz de Tenerife": (28.47, -16.25),
    "Segovia": (40.95, -4.12),
    "Sevilla": (37.39, -5.99),
    "Soria": (41.76, -2.47),
    "Tarragona": (41.12, 1.25),
    "Teruel": (40.34, -1.11),
    "Toledo": (39.86, -4.03),
    "Valencia": (39.47, -0.38),
    "Valladolid": (41.65, -4.72),
    "Vizcaya": (43.26, -2.94),
    "Zamora": (41.50, -5.75),
    "Zaragoza": (41.65, -0.89),
}


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    return fetch_farmacias()


def refresh_data() -> None:
    load_data.clear()


def import_master_excel(reset_before_import: bool = False) -> dict[str, object]:
    result = {
        "excel_exists": MASTER_XLSX.exists(),
        "sqlite_total": count_farmacias(),
        "message": "",
    }

    if not MASTER_XLSX.exists():
        result["message"] = "No se encontró data/farmacias_master.xlsx. Sube tu Excel real."
        return result

    try:
        if reset_before_import:
            reset_database()
        df, import_debug = load_farmacias_excel(MASTER_XLSX)
        upsert_farmacias(df)
        refresh_data()
        result.update(import_debug)
        result["sqlite_total"] = count_farmacias()
        result["message"] = f"Importadas o actualizadas {len(df)} farmacias desde el Excel real."
    except ValueError as exc:
        result["message"] = str(exc)
    except Exception as exc:
        result["message"] = f"No se pudo importar la hoja {MASTER_SHEET_NAME}: {exc}"

    return result


def apply_dashboard_style(theme: str) -> None:
    dark = theme == "Oscuro"
    bg = "#0f172a" if dark else "#f5f7fb"
    panel = "#111827" if dark else "#ffffff"
    text = "#f8fafc" if dark else "#111827"
    muted = "#94a3b8" if dark else "#64748b"
    border = "#1f2937" if dark else "#e5e7eb"
    st.markdown(
        f"""
        <style>
        .stApp {{ background: {bg}; color: {text}; }}
        section[data-testid="stSidebar"] {{ background: {panel}; border-right: 1px solid {border}; }}
        div[data-testid="stMetric"] {{
            background: {panel};
            border: 1px solid {border};
            border-radius: 8px;
            padding: 16px 18px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
        }}
        div[data-testid="stMetricLabel"] p {{ color: {muted}; font-size: 0.82rem; }}
        div[data-testid="stMetricValue"] {{ color: {text}; font-weight: 750; }}
        .section-title {{ font-size: 1.05rem; font-weight: 700; margin: 8px 0 10px; color: {text}; }}
        .page-subtitle {{ color: {muted}; margin-bottom: 18px; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def plot_theme(theme: str) -> str:
    return "plotly_dark" if theme == "Oscuro" else "plotly_white"


def normalize_funnel_state(value: object) -> str:
    state = str(value or "").strip()
    if state in {"Contactada IA", "Contactada manual"}:
        return "Contactada"
    if state in FUNNEL_STATES:
        return state
    return "No contactada"


def prepare_dashboard_data(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    for column in ["score_comercial", "score_compraventa", "facturacion_estimada", "auditorias_vendidas", "edad_titular"]:
        data[column] = pd.to_numeric(data.get(column, 0), errors="coerce").fillna(0)

    data["fecha_ultimo_contacto_dt"] = pd.to_datetime(data.get("fecha_ultimo_contacto", ""), errors="coerce")
    data["fase_embudo"] = data["estado_comercial"].apply(normalize_funnel_state)
    data["prioridad_label"] = data["prioridad"].map({"A": "Prioridad Alta", "B": "Prioridad Media", "C": "Prioridad Baja"}).fillna("Sin prioridad")
    data["es_cliente"] = data["estado_comercial"].eq("Cliente recurrente")
    data["es_prospecto"] = ~data["estado_comercial"].isin(["Cliente recurrente", "Descartada"])
    data["es_compraventa"] = data["score_compraventa"] >= 60
    data["probabilidad_transmision"] = pd.cut(data["score_compraventa"], [-1, 49, 74, 100], labels=["Baja", "Media", "Alta"]).astype(str)
    return data


def format_currency(value: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f} M€"
    if value >= 1_000:
        return f"{value / 1_000:.0f} k€"
    return f"{value:.0f} €"


def render_kpis(data: pd.DataFrame) -> None:
    values = [
        ("🏥 Total farmacias", f"{len(data):,}".replace(",", ".")),
        ("📣 Prospectadas", f"{int(data['estado_comercial'].ne('No contactada').sum()):,}".replace(",", ".")),
        ("📅 Reuniones agendadas", f"{int(data['fase_embudo'].eq('Reunión agendada').sum()):,}".replace(",", ".")),
        ("✅ Auditorías vendidas", f"{int(data['auditorias_vendidas'].sum()):,}".replace(",", ".")),
        ("🔁 Clientes recurrentes", f"{int(data['es_cliente'].sum()):,}".replace(",", ".")),
        ("💶 Facturación potencial anual", format_currency(float(data["facturacion_estimada"].sum()))),
        ("📈 Recurrente mensual estimado", format_currency(float(data.loc[data["es_cliente"], "facturacion_estimada"].sum() / 12))),
        ("🤝 Oportunidades compraventa", f"{int(data['es_compraventa'].sum()):,}".replace(",", ".")),
    ]
    rows = [st.columns(4), st.columns(4)]
    for idx, (label, value) in enumerate(values):
        rows[idx // 4][idx % 4].metric(label, value, delta="Sin histórico")


def funnel_chart(data: pd.DataFrame, theme: str) -> tuple[go.Figure, pd.DataFrame, float]:
    counts = data["fase_embudo"].value_counts().reindex(FUNNEL_STATES, fill_value=0).reset_index()
    counts.columns = ["fase", "farmacias"]
    counts["conversion_anterior"] = counts["farmacias"].div(counts["farmacias"].shift(1)).mul(100).round(1)
    counts.loc[0, "conversion_anterior"] = 100.0
    first = max(int(counts.iloc[0]["farmacias"]), 1)
    global_conversion = round((int(counts.iloc[-1]["farmacias"]) / first) * 100, 1)
    fig = go.Figure(
        go.Funnel(
            y=counts["fase"],
            x=counts["farmacias"],
            textinfo="value+percent initial",
            marker={"color": ["#64748b", "#38bdf8", "#22c55e", "#f59e0b", "#8b5cf6", "#0ea5e9", "#14b8a6"]},
            hovertemplate="<b>%{y}</b><br>Farmacias: %{x}<extra></extra>",
        )
    )
    fig.update_layout(template=plot_theme(theme), height=390, margin=dict(l=10, r=10, t=20, b=10))
    return fig, counts, global_conversion


def priority_donut(data: pd.DataFrame, theme: str) -> go.Figure:
    grouped = data["prioridad_label"].value_counts().reset_index()
    grouped.columns = ["prioridad", "farmacias"]
    fig = px.pie(grouped, names="prioridad", values="farmacias", hole=0.58)
    fig.update_traces(textinfo="label+percent+value")
    fig.update_layout(template=plot_theme(theme), height=390, margin=dict(l=10, r=10, t=20, b=10), showlegend=False)
    return fig


def opportunities_map(data: pd.DataFrame, theme: str) -> go.Figure:
    grouped = (
        data.groupby(["provincia", "municipio"], dropna=False)
        .agg(
            farmacias=("id_farmacia", "count"),
            clientes_activos=("es_cliente", "sum"),
            prospectos=("es_prospecto", "sum"),
            auditorias=("auditorias_vendidas", "sum"),
        )
        .reset_index()
    )
    grouped["coords_key"] = grouped["provincia"].where(grouped["provincia"].isin(SPAIN_PROVINCE_COORDS), grouped["municipio"])
    grouped["lat"] = grouped["coords_key"].map(lambda value: SPAIN_PROVINCE_COORDS.get(str(value), (40.42, -3.70))[0])
    grouped["lon"] = grouped["coords_key"].map(lambda value: SPAIN_PROVINCE_COORDS.get(str(value), (40.42, -3.70))[1])
    fig = px.scatter_geo(
        grouped,
        lat="lat",
        lon="lon",
        size="farmacias",
        color="farmacias",
        hover_name="municipio",
        hover_data={"provincia": True, "farmacias": True, "clientes_activos": True, "prospectos": True, "auditorias": True, "lat": False, "lon": False},
        color_continuous_scale="Blues",
        projection="natural earth",
    )
    fig.update_geos(visible=False, lonaxis_range=[-10, 5], lataxis_range=[35, 44.5], showcountries=True, countrycolor="#94a3b8")
    fig.update_layout(template=plot_theme(theme), height=430, margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False)
    return fig


def evolution_chart(data: pd.DataFrame, period: str, theme: str) -> go.Figure:
    days = {"Últimos 30 días": 30, "Últimos 90 días": 90, "Último año": 365}[period]
    max_date = data["fecha_ultimo_contacto_dt"].max()
    if pd.isna(max_date):
        max_date = pd.Timestamp.today().normalize()
    scoped = data[data["fecha_ultimo_contacto_dt"].between(max_date - pd.Timedelta(days=days), max_date)].copy()
    if scoped.empty:
        scoped = data.copy()
    scoped["periodo"] = scoped["fecha_ultimo_contacto_dt"].dt.to_period("W").dt.start_time
    grouped = (
        scoped.groupby("periodo")
        .agg(
            contactos=("id_farmacia", "count"),
            reuniones=("fase_embudo", lambda value: (value == "Reunión agendada").sum()),
            auditorias_vendidas=("auditorias_vendidas", "sum"),
            clientes_recurrentes=("estado_comercial", lambda value: (value == "Cliente recurrente").sum()),
        )
        .reset_index()
    )
    fig = px.line(grouped, x="periodo", y=["contactos", "reuniones", "auditorias_vendidas", "clientes_recurrentes"], markers=True)
    fig.update_layout(template=plot_theme(theme), height=360, margin=dict(l=10, r=10, t=20, b=10), legend_orientation="h")
    return fig


def economic_potential_chart(data: pd.DataFrame, dimension: str, theme: str) -> go.Figure:
    column = {"Provincia": "provincia", "Zona": "municipio", "Prioridad": "prioridad_label"}[dimension]
    grouped = data.groupby(column, dropna=False)["facturacion_estimada"].sum().sort_values(ascending=False).reset_index().head(20)
    fig = px.bar(grouped, x=column, y="facturacion_estimada", color="facturacion_estimada", color_continuous_scale="Teal")
    fig.update_layout(template=plot_theme(theme), height=380, margin=dict(l=10, r=10, t=20, b=10), coloraxis_showscale=False)
    fig.update_yaxes(tickprefix="€", separatethousands=True)
    return fig


def recent_activity(data: pd.DataFrame) -> pd.DataFrame:
    activity = data[data["fecha_ultimo_contacto_dt"].notna()].copy()
    if activity.empty:
        return pd.DataFrame(columns=["Fecha", "Actividad", "Farmacia", "Ciudad", "Detalle"])
    activity["Actividad"] = activity["fase_embudo"].map(
        {
            "Reunión agendada": "Reunión",
            "Auditoría propuesta": "Auditoría propuesta",
            "Auditoría vendida": "Auditoría vendida",
            "Cliente recurrente": "Cliente",
        }
    ).fillna("Contacto")
    activity["Detalle"] = activity["proxima_accion"].fillna("").replace("", activity["estado_comercial"])
    return (
        activity.sort_values("fecha_ultimo_contacto_dt", ascending=False)
        .assign(Fecha=lambda frame: frame["fecha_ultimo_contacto_dt"].dt.strftime("%Y-%m-%d"))
        [["Fecha", "Actividad", "nombre", "municipio", "Detalle"]]
        .rename(columns={"nombre": "Farmacia", "municipio": "Ciudad"})
        .head(30)
    )


def dashboard_view(df: pd.DataFrame) -> None:
    st.markdown("### Dashboard ejecutivo")
    st.markdown('<div class="page-subtitle">Estado comercial, captación, auditorías, clientes y oportunidades futuras.</div>', unsafe_allow_html=True)
    if df.empty:
        st.info("Importa el Excel maestro para cargar el CRM.")
        return

    theme = st.session_state.get("theme", "Claro")
    data = prepare_dashboard_data(df)
    render_kpis(data)

    funnel_col, donut_col = st.columns([1.45, 1])
    with funnel_col:
        st.markdown('<div class="section-title">Embudo comercial</div>', unsafe_allow_html=True)
        fig, conversion_table, global_conversion = funnel_chart(data, theme)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Conversión global: {global_conversion:.1f}%")
        st.dataframe(conversion_table, hide_index=True, use_container_width=True)
    with donut_col:
        st.markdown('<div class="section-title">Distribución de prospectos</div>', unsafe_allow_html=True)
        st.plotly_chart(priority_donut(data, theme), use_container_width=True)

    map_col, potential_col = st.columns([1.25, 1])
    with map_col:
        st.markdown('<div class="section-title">Mapa de oportunidades</div>', unsafe_allow_html=True)
        st.plotly_chart(opportunities_map(data, theme), use_container_width=True)
    with potential_col:
        st.markdown('<div class="section-title">Potencial económico</div>', unsafe_allow_html=True)
        dimension = st.selectbox("Agrupar potencial por", ["Provincia", "Zona", "Prioridad"], index=0)
        st.plotly_chart(economic_potential_chart(data, dimension, theme), use_container_width=True)

    top_col, buy_col = st.columns(2)
    with top_col:
        st.markdown('<div class="section-title">Top 20 oportunidades comerciales</div>', unsafe_allow_html=True)
        top = (
            data.sort_values("score_comercial", ascending=False)
            .loc[:, ["nombre", "municipio", "score_comercial", "prioridad", "proxima_accion", "fecha_ultimo_contacto"]]
            .rename(
                columns={
                    "nombre": "Nombre farmacia",
                    "municipio": "Ciudad",
                    "score_comercial": "Score comercial",
                    "prioridad": "Prioridad",
                    "proxima_accion": "Próxima acción",
                    "fecha_ultimo_contacto": "Última interacción",
                }
            )
            .head(20)
        )
        st.dataframe(top, hide_index=True, use_container_width=True)
    with buy_col:
        st.markdown('<div class="section-title">Oportunidades de compraventa</div>', unsafe_allow_html=True)
        compraventa = (
            data.sort_values("score_compraventa", ascending=False)
            .loc[:, ["nombre", "municipio", "edad_titular", "score_compraventa", "probabilidad_transmision", "observaciones"]]
            .rename(
                columns={
                    "nombre": "Farmacia",
                    "municipio": "Ciudad",
                    "edad_titular": "Edad titular",
                    "score_compraventa": "Score compraventa",
                    "probabilidad_transmision": "Probabilidad transmisión",
                    "observaciones": "Observaciones",
                }
            )
            .head(20)
        )
        st.dataframe(compraventa, hide_index=True, use_container_width=True)

    evolution_col, activity_col = st.columns([1.3, 1])
    with evolution_col:
        st.markdown('<div class="section-title">Evolución comercial</div>', unsafe_allow_html=True)
        period = st.selectbox("Periodo", ["Últimos 30 días", "Últimos 90 días", "Último año"], index=1)
        st.plotly_chart(evolution_chart(data, period, theme), use_container_width=True)
    with activity_col:
        st.markdown('<div class="section-title">Actividad reciente</div>', unsafe_allow_html=True)
        st.dataframe(recent_activity(data), hide_index=True, use_container_width=True)


def filter_table(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    search = st.text_input("Buscar por nombre, municipio, provincia o titular")
    c1, c2, c3, c4 = st.columns(4)
    estado = c1.multiselect("Estado comercial", ESTADOS_COMERCIALES)
    provincia = c2.multiselect("Provincia", sorted(data["provincia"].dropna().unique().tolist()))
    prioridad = c3.multiselect("Prioridad", ["A", "B", "C"])
    min_score = c4.slider("Score comercial mínimo", 0, 100, 0)

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
    return data[pd.to_numeric(data["score_comercial"], errors="coerce").fillna(0) >= min_score]


def table_view(df: pd.DataFrame) -> None:
    st.subheader("Farmacias")
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


def placeholder_view(title: str, df: pd.DataFrame) -> None:
    st.subheader(title)
    if df.empty:
        st.info("No hay datos disponibles.")
        return
    dashboard_view(df)


def main() -> None:
    init_db()
    if "startup_import_debug" not in st.session_state:
        st.session_state["startup_import_debug"] = import_master_excel(reset_before_import=True)

    df = load_data()

    with st.sidebar:
        st.title("CRM Farmacias")
        st.session_state["theme"] = st.radio("Tema", ["Claro", "Oscuro"], horizontal=True)
        page = st.radio(
            "Navegación",
            ["Dashboard", "Farmacias", "Pipeline Comercial", "Auditorías", "Clientes", "Compraventa", "Analítica", "Configuración"],
        )
        st.caption(f"SQLite: {DB_PATH}")

    apply_dashboard_style(st.session_state["theme"])
    st.title("CRM Farmacias")
    st.caption("CRM interno para embudo comercial, scoring, compraventa y analítica de farmacias españolas.")

    if page == "Dashboard":
        dashboard_view(df)
    elif page == "Farmacias":
        table_view(df)
    elif page == "Pipeline Comercial":
        dashboard_view(df)
    elif page == "Auditorías":
        dashboard_view(df)
    elif page == "Clientes":
        table_view(df[df["estado_comercial"].eq("Cliente recurrente")] if not df.empty else df)
    elif page == "Compraventa":
        dashboard_view(df)
    elif page == "Analítica":
        dashboard_view(df)
    else:
        import_excel_view()


if __name__ == "__main__":
    main()
