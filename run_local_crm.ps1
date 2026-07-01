$ErrorActionPreference = "Stop"

if (!(Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Creado .env desde .env.example. Revisa rutas si lo necesitas."
}

$python = "C:\Users\Manuel\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if (!(Test-Path $python)) {
  $python = "python"
}

& $python -m scripts.init_local_crm
& $python -m uvicorn local_crm.main:app --host 0.0.0.0 --port 8000 --reload
