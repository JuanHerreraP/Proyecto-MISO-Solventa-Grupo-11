"""Imprime la conciliación de la telemetría paramétrica (HU20, EC — contrapresión).

Lee los conteos de la cola SQS principal, de su DLQ y de la base de datos, y muestra la identidad
`aceptados == procesados + en_cola + en_dlq`. Pensado para ejecutarse como tarea puntual de ECS
(RunTask con command override), en la misma red y con las mismas credenciales de RDS que el
backend, igual que `crear_admin.py`.

Variables de entorno:
    SQS_QUEUE_URL        URL de la cola principal (obligatoria).
    SQS_DLQ_URL          URL de la DLQ (opcional).
    AWS_DEFAULT_REGION   Región de AWS.
    ACEPTADOS            Opcional: total de eventos aceptados por la ingesta (contador/métrica),
                         para verificar que la identidad cuadra.

El entrypoint ya construye DATABASE_URL a partir de DB_HOST/DB_PASSWORD, pero este script también
lo hace por si se invoca directamente, para no depender del orden.
"""

import os
import sys
from urllib.parse import quote


def _asegurar_database_url() -> None:
    if os.environ.get("DATABASE_URL"):
        return
    if not os.environ.get("DB_HOST"):
        return
    usuario = quote(os.environ.get("DB_USER", "solventa"), safe="")
    password = quote(os.environ.get("DB_PASSWORD", ""), safe="")
    os.environ["DATABASE_URL"] = (
        f"postgresql+psycopg://{usuario}:{password}@{os.environ['DB_HOST']}"
        ":5432/solventa?sslmode=require"
    )


def main() -> int:
    url_cola = os.environ.get("SQS_QUEUE_URL")
    if not url_cola:
        print("ERROR: SQS_QUEUE_URL es obligatorio.", file=sys.stderr)
        return 2
    url_dlq = os.environ.get("SQS_DLQ_URL")

    _asegurar_database_url()

    import boto3

    from app.infraestructura.database import SessionLocal, esperar_base_disponible
    from app.siniestros.conciliacion import conciliar

    esperar_base_disponible()
    sqs = boto3.client("sqs", region_name=os.environ.get("AWS_DEFAULT_REGION"))

    db = SessionLocal()
    try:
        resultado = conciliar(db, sqs, url_cola, url_dlq)
    finally:
        db.close()

    print("=== Conciliación de telemetría paramétrica (HU20) ===")
    print(f"Procesados en BD (registrado_por=TELEMETRIA): {resultado.procesados_bd}")
    print(f"En cola (ApproximateNumberOfMessages):        {resultado.en_cola}")
    print(f"En vuelo (NotVisible):                        {resultado.en_vuelo}")
    print(f"En DLQ:                                       {resultado.en_dlq}")
    print(f"Total observado:                              {resultado.total_observado}")

    aceptados_env = os.environ.get("ACEPTADOS")
    if aceptados_env is not None:
        aceptados = int(aceptados_env)
        cuadra = resultado.cuadra(aceptados)
        print(f"Aceptados (ingesta):                          {aceptados}")
        print(f"¿Cuadra (aceptados == total observado)?       {'SÍ' if cuadra else 'NO'}")
        return 0 if cuadra else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
