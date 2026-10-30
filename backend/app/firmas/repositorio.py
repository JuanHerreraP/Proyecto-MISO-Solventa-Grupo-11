"""Adaptadores de persistencia de la firma y de los datos del titular (HU14 / BPM-60)."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.firmas.contrato import TitularContrato
from app.firmas.modelos import ProcesoFirma
from app.firmas.modelos_db import ProcesoFirmaDB
from app.identidad.modelos_db import UsuarioDB

_FECHAS = ("otp_emitido_en", "otp_expira_en", "firmado_en", "creado_en", "actualizado_en")


class RepositorioFirmasEnMemoria:
    def __init__(self):
        self._por_cotizacion: dict[str, ProcesoFirma] = {}

    def crear(self, proceso: ProcesoFirma) -> bool:
        if proceso.cotizacion_id in self._por_cotizacion:
            return False
        self._por_cotizacion[proceso.cotizacion_id] = proceso.model_copy(deep=True)
        return True

    def guardar(self, proceso: ProcesoFirma) -> None:
        self._por_cotizacion[proceso.cotizacion_id] = proceso.model_copy(deep=True)

    def obtener_por_cotizacion(self, cotizacion_id: str) -> ProcesoFirma | None:
        proceso = self._por_cotizacion.get(cotizacion_id)
        return proceso.model_copy(deep=True) if proceso else None


class RepositorioFirmasPostgres:
    def __init__(self, db: Session):
        self._db = db

    def crear(self, proceso: ProcesoFirma) -> bool:
        self._db.add(ProcesoFirmaDB(**self._a_persistencia(proceso)))
        try:
            self._db.commit()
        except IntegrityError:
            self._db.rollback()
            return False
        return True

    def guardar(self, proceso: ProcesoFirma) -> None:
        persistido = self._db.get(ProcesoFirmaDB, proceso.firma_id)
        datos = self._a_persistencia(proceso)
        if persistido is None:
            self._db.add(ProcesoFirmaDB(**datos))
        else:
            for campo, valor in datos.items():
                setattr(persistido, campo, valor)
        self._db.commit()

    def obtener_por_cotizacion(self, cotizacion_id: str) -> ProcesoFirma | None:
        sentencia = select(ProcesoFirmaDB).where(ProcesoFirmaDB.cotizacion_id == cotizacion_id)
        return self._a_dominio(self._db.scalars(sentencia).first())

    @staticmethod
    def _a_persistencia(proceso: ProcesoFirma) -> dict[str, object]:
        datos = proceso.model_dump(exclude={"contrato"})
        datos["contrato"] = proceso.contrato.model_dump(mode="json")
        datos["estado"] = proceso.estado.value
        datos["otp_canal"] = proceso.otp_canal.value if proceso.otp_canal else None
        return datos

    @staticmethod
    def _a_dominio(persistido: ProcesoFirmaDB | None) -> ProcesoFirma | None:
        if persistido is None:
            return None
        datos = {c.name: getattr(persistido, c.name) for c in ProcesoFirmaDB.__table__.columns}
        for campo in _FECHAS:
            datos[campo] = _con_zona(datos[campo])
        return ProcesoFirma.model_validate(datos)


class RepositorioTitularesPostgres:
    """Lee del módulo de identidad los datos del titular que van en el contrato."""

    def __init__(self, db: Session):
        self._db = db

    def obtener(self, cliente_id: str) -> TitularContrato | None:
        try:
            usuario = self._db.get(UsuarioDB, UUID(cliente_id))
        except ValueError:
            return None
        if usuario is None:
            return None
        return TitularContrato(
            nombre_completo=f"{usuario.nombre} {usuario.apellido}",
            tipo_documento=usuario.tipo_documento,
            numero_documento=usuario.numero_documento,
            email=usuario.email,
            celular=usuario.celular,
        )


def _con_zona(fecha: datetime | None) -> datetime | None:
    if fecha is None:
        return None
    return fecha.replace(tzinfo=UTC) if fecha.tzinfo is None else fecha
