"""Caso de uso: generar el perfil de riesgo individualizado y su dictamen de suscripción."""

import time
import uuid
from datetime import datetime, timezone

from app.perfilamiento.dominio import reglas
from app.perfilamiento.dominio.modelos import (
    Dictamen,
    OfertaCliente,
    PerfilRiesgo,
    SenalesPerfilamiento,
)
from app.perfilamiento.repositorio import RepositorioPerfiles


class ConsentimientoNoVigente(Exception):
    """El cliente no tiene un consentimiento vigente para usar sus datos."""


EXPLICACION_CLIENTE = {
    Dictamen.ACEPTADO: "Tu solicitud fue aprobada con la tarifa estándar.",
    Dictamen.AJUSTADO: (
        "Tu solicitud fue aprobada con un ajuste en el precio, de acuerdo con la "
        "información financiera y del inmueble que autorizaste consultar."
    ),
    Dictamen.RECHAZADO: (
        "Por ahora no podemos ofrecerte esta cobertura con la información que autorizaste "
        "consultar. Puedes pedir la revisión de tu caso con un asesor."
    ),
}


class ServicioPerfilamiento:
    def __init__(self, repositorio: RepositorioPerfiles):
        self._repositorio = repositorio

    def generar_perfil(self, senales: SenalesPerfilamiento) -> PerfilRiesgo:
        if not senales.consentimiento_vigente:
            raise ConsentimientoNoVigente(senales.cliente_id)

        inicio = time.perf_counter()
        resultado = reglas.evaluar(senales)
        tiempo_ms = round((time.perf_counter() - inicio) * 1000, 3)

        perfil = PerfilRiesgo(
            perfil_id=str(uuid.uuid4()),
            cliente_id=senales.cliente_id,
            consentimiento_id=senales.consentimiento_id,
            puntaje_riesgo=resultado.puntaje_riesgo,
            clasificacion=resultado.clasificacion,
            dictamen=resultado.dictamen,
            factor_riesgo=resultado.factor_riesgo,
            extraprima_porcentaje=resultado.extraprima_porcentaje,
            origen_senales=senales.origen,
            version_reglas=reglas.VERSION_REGLAS,
            reglas_aplicadas=resultado.reglas_aplicadas,
            fecha_calculo=datetime.now(timezone.utc),
            tiempo_calculo_ms=tiempo_ms,
        )
        self._repositorio.guardar(perfil)
        return perfil

    def consultar_perfil(self, cliente_id: str) -> PerfilRiesgo | None:
        return self._repositorio.obtener(cliente_id)


def a_oferta_cliente(perfil: PerfilRiesgo) -> OfertaCliente:
    """Reduce el perfil a lo que puede ver el cliente: sin puntaje ni reglas internas."""
    return OfertaCliente(
        cliente_id=perfil.cliente_id,
        dictamen=perfil.dictamen,
        extraprima_porcentaje=perfil.extraprima_porcentaje,
        explicacion=EXPLICACION_CLIENTE[perfil.dictamen],
        fecha_calculo=perfil.fecha_calculo,
    )
