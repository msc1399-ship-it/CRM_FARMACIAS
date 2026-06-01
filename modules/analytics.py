import pandas as pd


def pipeline_summary(df: pd.DataFrame) -> dict[str, int | float]:
    if df.empty:
        return {
            "total_farmacias": 0,
            "clientes_activos": 0,
            "auditorias_vendidas": 0,
            "score_comercial_medio": 0.0,
            "score_compraventa_medio": 0.0,
        }

    return {
        "total_farmacias": int(len(df)),
        "clientes_activos": int((df["estado_comercial"] == "Cliente recurrente").sum()),
        "auditorias_vendidas": int(pd.to_numeric(df["auditorias_vendidas"], errors="coerce").fillna(0).sum()),
        "score_comercial_medio": float(pd.to_numeric(df["score_comercial"], errors="coerce").fillna(0).mean()),
        "score_compraventa_medio": float(pd.to_numeric(df["score_compraventa"], errors="coerce").fillna(0).mean()),
    }


def count_by(df: pd.DataFrame, column: str, label: str) -> pd.DataFrame:
    if df.empty or column not in df.columns:
        return pd.DataFrame(columns=[label, "farmacias"])

    return (
        df[column]
        .fillna("Sin dato")
        .replace("", "Sin dato")
        .value_counts()
        .rename_axis(label)
        .reset_index(name="farmacias")
    )


def proximas_acciones(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    cols = ["nombre", "municipio", "provincia", "estado_comercial", "prioridad", "proxima_accion", "fecha_ultimo_contacto"]
    data = df[df["proxima_accion"].fillna("").astype(str).str.strip() != ""].copy()
    return data.sort_values(["prioridad", "fecha_ultimo_contacto"], ascending=[True, False])[cols]


def ranking_prioritarias(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    cols = [
        "id_farmacia",
        "nombre",
        "municipio",
        "provincia",
        "titular",
        "estado_comercial",
        "prioridad",
        "score_comercial",
        "score_compraventa",
        "accion_recomendada",
    ]
    return df.sort_values(["score_comercial", "score_compraventa"], ascending=False)[cols]
