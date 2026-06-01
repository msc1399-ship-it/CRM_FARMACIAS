# CRM Farmacias

Aplicación Streamlit para gestionar una base interna de farmacias españolas con importación desde Excel, embudo comercial, scoring comercial, scoring de compraventa y analítica.

## Requisitos

```bash
pip install -r requirements.txt
```

## Ejecucion

```bash
streamlit run app.py
```

## Datos

La aplicacion persiste localmente en `data/crm_farmacias.db`. Ese archivo no se versiona en Git para evitar publicar datos reales; se crea automaticamente al ejecutar la app.

El Excel maestro debe incluir estas columnas obligatorias:

- `id_farmacia`
- `nombre`
- `municipio`
- `provincia`
- `titular`

Columnas opcionales recomendadas:

- `telefono`
- `email`
- `estado_comercial`
- `proxima_accion`
- `fecha_ultimo_contacto`
- `observaciones`
- `potencial_comercial`
- `facturacion_estimada`
- `rentabilidad_estimada`
- `edad_titular`
- `empleados`
- `interes_compraventa`
- `visitas_realizadas`
- `auditorias_vendidas`

El archivo operativo debe llamarse `data/farmacias_master.xlsx` y debe contener una hoja llamada `Farmacias`. Este Excel no se versiona para evitar publicar datos reales.

## Estados comerciales permitidos

- No contactada
- Contactada IA
- Contactada manual
- Interesada
- Reunión agendada
- Auditoría propuesta
- Auditoría vendida
- Cliente recurrente
- Descartada
