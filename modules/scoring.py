import pandas as pd


ESTADOS_COMERCIALES = [
    "No contactada",
    "Contactada IA",
    "Contactada manual",
    "Interesada",
    "Reunión agendada",
    "Auditoría propuesta",
    "Auditoría vendida",
    "Cliente recurrente",
    "Descartada",
]


ESTADO_SCORE = {
    "No contactada": 8,
    "Contactada IA": 18,
    "Contactada manual": 24,
    "Interesada": 42,
    "Reunión agendada": 58,
    "Auditoría propuesta": 72,
    "Auditoría vendida": 88,
    "Cliente recurrente": 96,
    "Descartada": 0,
}


def _num(series: pd.Series | int | float, default: float = 0) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(default)


def calcular_prioridad(score: float) -> str:
    if score >= 75:
        return "A"
    if score >= 50:
        return "B"
    return "C"


def calcular_score_comercial(row: pd.Series) -> float:
    estado = str(row.get("estado_comercial", "No contactada")).strip()
    potencial = float(row.get("potencial_comercial", 0) or 0)
    facturacion = float(row.get("facturacion_estimada", 0) or 0)
    visitas = float(row.get("visitas_realizadas", 0) or 0)
    auditorias = float(row.get("auditorias_vendidas", 0) or 0)

    estado_component = ESTADO_SCORE.get(estado, 8)
    potencial_component = min(max(potencial, 0), 100) * 0.35
    facturacion_component = min(max(facturacion, 0), 2_000_000) / 2_000_000 * 25
    auditoria_component = min(max(auditorias, 0), 3) * 6
    visitas_penalty = min(max(visitas, 0), 12) * 1.5

    return round(min(max(estado_component + potencial_component + facturacion_component + auditoria_component - visitas_penalty, 0), 100), 1)


def calcular_score_compraventa(row: pd.Series) -> float:
    edad_titular = float(row.get("edad_titular", 0) or 0)
    facturacion = float(row.get("facturacion_estimada", 0) or 0)
    rentabilidad = float(row.get("rentabilidad_estimada", 0) or 0)
    empleados = float(row.get("empleados", 0) or 0)
    interes = str(row.get("interes_compraventa", "Medio")).strip().lower()

    edad_component = max(min((edad_titular - 45) * 1.2, 28), 0)
    facturacion_component = min(max(facturacion, 0), 2_000_000) / 2_000_000 * 24
    rentabilidad_component = min(max(rentabilidad, 0), 35) / 35 * 22
    equipo_component = min(max(empleados, 0), 12) / 12 * 10
    interes_component = {"alto": 16, "medio": 8, "bajo": 2}.get(interes, 8)

    return round(min(max(edad_component + facturacion_component + rentabilidad_component + equipo_component + interes_component, 0), 100), 1)


def aplicar_scoring(df: pd.DataFrame) -> pd.DataFrame:
    scored = df.copy()
    scored["potencial_comercial"] = _num(scored["potencial_comercial"])
    scored["facturacion_estimada"] = _num(scored["facturacion_estimada"])
    scored["rentabilidad_estimada"] = _num(scored["rentabilidad_estimada"])
    scored["edad_titular"] = _num(scored["edad_titular"])
    scored["empleados"] = _num(scored["empleados"])
    scored["visitas_realizadas"] = _num(scored["visitas_realizadas"]).astype(int)
    scored["auditorias_vendidas"] = _num(scored["auditorias_vendidas"]).astype(int)
    scored["score_comercial"] = scored.apply(calcular_score_comercial, axis=1)
    scored["score_compraventa"] = scored.apply(calcular_score_compraventa, axis=1)
    scored["prioridad"] = scored["score_comercial"].apply(calcular_prioridad)
    scored["accion_recomendada"] = scored.apply(recomendar_accion, axis=1)
    return scored


def recomendar_accion(row: pd.Series) -> str:
    estado = str(row.get("estado_comercial", "No contactada"))
    prioridad = str(row.get("prioridad", "C"))
    score_cv = float(row.get("score_compraventa", 0) or 0)

    if estado == "Descartada":
        return "Mantener descartada salvo nueva senal comercial."
    if estado in {"Auditoría vendida", "Cliente recurrente"}:
        return "Preparar seguimiento de valor y venta cruzada."
    if prioridad == "A" and score_cv >= 70:
        return "Agendar reunion directiva y explorar oportunidad de compraventa."
    if prioridad == "A":
        return "Contactar esta semana y proponer auditoría."
    if prioridad == "B":
        return "Hacer seguimiento y cualificar interes."
    return "Nutrir en base de datos y revisar en proxima campana."
