"""Tarea diaria de la renovación automática (HU17 / BPM-69).

Se ejecuta una vez al día (en AWS, una tarea programada de EventBridge sobre la imagen del
backend; en local, a mano o con cron):

    python -m app.polizas.tarea_renovacion_automatica

Envía los preavisos, cobra las renovaciones que vencen hoy y da seguimiento a los ciclos
abiertos. Es idempotente: ejecutarla dos veces el mismo día no repite correos ni cobros. Sale con
código 1 si alguna póliza falló, para que la ejecución quede marcada en el monitoreo.
"""

import logging
import sys

from app.api.renovacion_automatica import construir_servicio
from app.infraestructura.database import SessionLocal

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    # Arma la aplicación como al arrancar la API: espera la base, registra todos los modelos y
    # crea las tablas que falten (entre ellas las de la renovación automática).
    import app.main  # noqa: F401

    db = SessionLocal()
    try:
        resultado = construir_servicio(db).ejecutar()
    finally:
        db.close()
    print(resultado.model_dump_json(indent=2))
    return 1 if resultado.errores else 0


if __name__ == "__main__":
    sys.exit(main())
