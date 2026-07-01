import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

import requests

from local_crm.config import ANALYTICS_API_URL, ANALYTICS_COMMAND


def run_analysis(expediente_id: int, documents_path: Path) -> dict[str, Any]:
    payload = {"expediente_id": expediente_id, "documents_path": str(documents_path)}

    if ANALYTICS_API_URL:
        response = requests.post(ANALYTICS_API_URL, json=payload, timeout=300)
        response.raise_for_status()
        return response.json()

    if ANALYTICS_COMMAND:
        command = shlex.split(ANALYTICS_COMMAND) + [str(documents_path)]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr or completed.stdout or "El analizador devolvio error")
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError:
            return {"status": "ok", "resumen": completed.stdout.strip(), "raw_stdout": completed.stdout}

    return {
        "status": "pending",
        "resumen": "Puente analitico configurado, pero ANALYTICS_API_URL o ANALYTICS_COMMAND no estan definidos.",
        "documents_path": str(documents_path),
    }
