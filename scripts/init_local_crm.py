from pathlib import Path

from local_crm.config import CRM_DB_PATH, CRM_EXCEL_PATH, EXPEDIENTES_ROOT
from local_crm.db import init_db
from local_crm.importer import import_farmacias


def main() -> None:
    print(f"SQLite: {CRM_DB_PATH}")
    print(f"Excel: {CRM_EXCEL_PATH}")
    print(f"Expedientes: {EXPEDIENTES_ROOT}")

    if not CRM_EXCEL_PATH.exists():
        raise SystemExit(f"No existe el Excel configurado: {CRM_EXCEL_PATH}")

    init_db(CRM_DB_PATH)
    EXPEDIENTES_ROOT.mkdir(parents=True, exist_ok=True)
    count = import_farmacias(Path(CRM_EXCEL_PATH), reset=True)
    print(f"Importadas {count} farmacias.")


if __name__ == "__main__":
    main()
