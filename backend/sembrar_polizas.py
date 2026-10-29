"""Siembra pólizas de demostración en la billetera de un cliente (HU07 / BPM-31).

Mientras no exista la emisión automática (HU12), la billetera no tiene de dónde sacar
pólizas. Este script le crea a un cliente ya registrado cinco pólizas que cubren los
casos de la historia: dos vigentes, una vencida, una cancelada y una paramétrica vigente
de retraso de vuelo (AV123 / BOG, umbral 180 minutos) para la demo de telemetría (HU20).

Es idempotente: si se vuelve a ejecutar, actualiza las mismas pólizas en vez de duplicarlas.
Solo para desarrollo y pruebas; no debe ejecutarse contra producción.

Uso:
    CLIENTE_EMAIL=ana@gmail.com python sembrar_polizas.py
"""

import os
import secrets
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal


def _polizas_demo(usuario, hoy: date):
    from app.polizas.dominio.modelos import (
        CoberturaPoliza,
        EstadoRegistroPoliza,
        Poliza,
        RamoPoliza,
    )

    prefijos = {
        RamoPoliza.VIAJE: "VJ",
        RamoPoliza.PROTECCION_DISPOSITIVOS: "DP",
        RamoPoliza.VIDA: "VD",
        RamoPoliza.PARAMETRICO: "PM",
    }
    sufijo = str(usuario.id).replace("-", "")[:8].upper()
    titular = f"{usuario.nombre} {usuario.apellido}"
    emitida = datetime.now(UTC)

    def crear(
        n,
        ramo,
        inicio,
        fin,
        prima,
        cobertura,
        suma,
        estado=EstadoRegistroPoliza.VIGENTE,
        descripcion_cobertura=None,
    ):
        return Poliza(
            poliza_id=f"DEMO-{sufijo}-{n}",
            numero_poliza=f"SOL-{prefijos[ramo]}-{sufijo}-{n}",
            cliente_id=str(usuario.id),
            ramo=ramo,
            estado=estado,
            titular_nombre=titular,
            titular_tipo_documento=usuario.tipo_documento,
            titular_numero_documento=usuario.numero_documento,
            fecha_inicio=inicio,
            fecha_fin=fin,
            prima_total=Decimal(prima),
            cobertura_principal=CoberturaPoliza(
                codigo=cobertura.upper().replace(" ", "_")[:50],
                nombre=cobertura,
                suma_asegurada=Decimal(suma),
                descripcion=descripcion_cobertura,
            ),
            codigo_verificacion=secrets.token_hex(8),
            emitida_en=emitida,
            cancelada_en=emitida if estado is EstadoRegistroPoliza.CANCELADA else None,
        )

    return [
        crear(
            "01",
            RamoPoliza.VIAJE,
            hoy - timedelta(days=5),
            hoy + timedelta(days=25),
            "85000.00",
            "Asistencia médica en viaje",
            "40000000.00",
        ),
        crear(
            "02",
            RamoPoliza.PROTECCION_DISPOSITIVOS,
            hoy - timedelta(days=60),
            hoy + timedelta(days=305),
            "240000.00",
            "Daño accidental del celular",
            "3500000.00",
        ),
        crear(
            "03",
            RamoPoliza.VIDA,
            hoy - timedelta(days=400),
            hoy - timedelta(days=35),
            "620000.00",
            "Muerte por cualquier causa",
            "150000000.00",
        ),
        crear(
            "04",
            RamoPoliza.PARAMETRICO,
            hoy - timedelta(days=20),
            hoy + timedelta(days=10),
            "45000.00",
            "Evento climático",
            "500000.00",
            estado=EstadoRegistroPoliza.VIGENTE,
            # Condición paramétrica legible por Solventa al cruzar los eventos de telemetría
            # (HU20): mismos códigos que el catálogo de cotización. El vuelo y la ubicación
            # coinciden con el proveedor simulado (AV123 / BOG) y el umbral es 180 minutos.
            descripcion_cobertura=(
                "tipo_evento=EVENTO_CLIMATICO; numero_vuelo=AV321; ubicacion=BOG; "
                "umbral_disparo=180; unidad=MINUTOS"
            ),
        ),
        crear(
            "05",
            RamoPoliza.VIAJE,
            hoy - timedelta(days=90),
            hoy + timedelta(days=90),
            "90000.00",
            "Asistencia médica en viaje",
            "40000000.00",
            estado=EstadoRegistroPoliza.CANCELADA,
        ),
        crear(
            "06",
            RamoPoliza.PARAMETRICO,
            hoy - timedelta(days=20),
            hoy + timedelta(days=10),
            "45000.00",
            "Retraso de vuelo",
            "500000.00",
            estado=EstadoRegistroPoliza.VIGENTE,
            # Condición paramétrica legible por Solventa al cruzar los eventos de telemetría
            # (HU20): mismos códigos que el catálogo de cotización. El vuelo y la ubicación
            # coinciden con el proveedor simulado (AV123 / BOG) y el umbral es 180 minutos.
            descripcion_cobertura=(
                "tipo_evento=RETRASO_VUELO; numero_vuelo=PV456; ubicacion=BOG; "
                "umbral_disparo=180; unidad=MINUTOS"
            ),
        ),
        crear(
            "07",
            RamoPoliza.PARAMETRICO,
            hoy - timedelta(days=20),
            hoy + timedelta(days=10),
            "45000.00",
            "Evento climático",
            "500000.00",
            estado=EstadoRegistroPoliza.VIGENTE,
            # Condición paramétrica legible por Solventa al cruzar los eventos de telemetría
            # (HU20): mismos códigos que el catálogo de cotización. El vuelo y la ubicación
            # coinciden con el proveedor simulado (AV123 / BOG) y el umbral es 180 minutos.
            descripcion_cobertura=(
                "tipo_evento=EVENTO_CLIMATICO; numero_vuelo=zV321; ubicacion=BOG; "
                "umbral_disparo=180; unidad=MINUTOS"
            ),
        ),
    ]


def main() -> int:
    email = os.environ.get("CLIENTE_EMAIL")
    if not email:
        print("ERROR: CLIENTE_EMAIL es obligatorio.", file=sys.stderr)
        return 2

    from sqlalchemy import select

    from app.identidad.modelos_db import UsuarioDB
    from app.infraestructura.database import Base, SessionLocal, engine, esperar_base_disponible
    from app.polizas import modelos_db  # noqa: F401
    from app.polizas.dominio.modelos import hoy_en_colombia
    from app.polizas.repositorio import RepositorioPolizasPostgres

    esperar_base_disponible()
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        usuario = db.scalar(select(UsuarioDB).where(UsuarioDB.email == email.strip().lower()))
        if usuario is None:
            print(f"ERROR: no existe un usuario con el correo {email}.", file=sys.stderr)
            return 1
        if usuario.rol != "CLIENTE":
            print(f"ERROR: {email} no es un cliente (rol {usuario.rol}).", file=sys.stderr)
            return 1

        repositorio = RepositorioPolizasPostgres(db)
        hoy = hoy_en_colombia(datetime.now(UTC))
        polizas = _polizas_demo(usuario, hoy)
        for poliza in polizas:
            repositorio.guardar(poliza)
            print(f"{poliza.numero_poliza}  {poliza.ramo.value:<24} {poliza.estado_en(hoy).value}")
        print(f"{len(polizas)} pólizas listas en la billetera de {email}.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
