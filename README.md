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

## Backend local FastAPI

Nueva arquitectura local desacoplada para trabajar desde este PC y acceder desde otro equipo por Tailscale:

```text
local_crm/
├─ main.py              # API FastAPI + servidor HTML
├─ db.py                # SQLite y esquema
├─ importer.py          # Importacion desde FARMACIAS_CYL.xlsx
├─ analytics_bridge.py  # Puente hacia API/comando analitico local
├─ config.py            # Configuracion .env
├─ templates/crm.html   # Plantilla dinamica basada en el HTML visual
└─ static/
   ├─ styles.css
   └─ app.js
scripts/init_local_crm.py
run_local_crm.ps1
.env.example
requirements_local.txt
```

Inicializacion:

```powershell
pip install -r requirements_local.txt
.\run_local_crm.ps1
```

El servidor escucha en `0.0.0.0:8000`, por lo que podras abrirlo desde el portatil usando la IP de Tailscale del PC servidor.

El CRM no modifica el software analitico existente. Para integrarlo, configura en `.env` una de estas opciones:

- `ANALYTICS_API_URL`: endpoint local que recibe la ruta del expediente.
- `ANALYTICS_COMMAND`: comando local al que se le pasa la ruta del expediente como argumento final.
