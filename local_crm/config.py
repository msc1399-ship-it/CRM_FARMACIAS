import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


ROOT_DIR = Path(__file__).resolve().parents[1]
if load_dotenv:
    load_dotenv(ROOT_DIR / ".env")


def _path_env(name: str, default: Path) -> Path:
    return Path(os.getenv(name, str(default))).expanduser().resolve()


CRM_DB_PATH = _path_env("CRM_DB_PATH", ROOT_DIR / "local_data" / "crm_farmacias.sqlite")
CRM_EXCEL_PATH = _path_env(
    "CRM_EXCEL_PATH",
    Path(r"C:\Users\Manuel\Desktop\PROYECTO\BASE_DATOS\FARMACIAS_CYL.xlsx"),
)
EXPEDIENTES_ROOT = _path_env("EXPEDIENTES_ROOT", ROOT_DIR / "local_data" / "expedientes")
ANALYTICS_API_URL = os.getenv("ANALYTICS_API_URL", "").strip()
ANALYTICS_COMMAND = os.getenv("ANALYTICS_COMMAND", "").strip()

SERVER_HOST = os.getenv("CRM_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("CRM_PORT", "8000"))
