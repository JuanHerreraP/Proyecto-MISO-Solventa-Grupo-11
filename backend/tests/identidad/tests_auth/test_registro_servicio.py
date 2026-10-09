from datetime import datetime, timezone

import pytest

from app.identidad.modelos import (
    Rol,
    VerificationResult,
    VerificationStatus,
)
from app.identidad.servicio import (
    ConsentimientoRequeridoError,
    KYCPendienteError,
    KYCRechazadoError,
    ServicioIdentidad,
    UsuarioYaExisteError,
)

from .conftest import FakeProviderKYC


def _resultado_kyc(
    estado: VerificationStatus,
) -> VerificationResult:
    return VerificationResult(
        verification_id="KYC-TEST-001",
        status=estado,
        risk_score=0.50,
        provider_name="proveedor-test",
        checked_at=datetime.now(timezone.utc),
    )


def test_registro_exitoso_crea_usuario(
    repositorio,
    solicitud_registro,
    resultado_kyc_aprobado,
):
    provider = FakeProviderKYC(
        resultado_kyc_aprobado
    )

    servicio = ServicioIdentidad(
        repositorio=repositorio,
        provider=provider,
    )

    resultado = servicio.registrar_usuario(
        solicitud_registro
    )

    usuario_guardado = (
        repositorio.buscar_por_email(
            "ana@gmail.com"
        )
    )

    assert usuario_guardado is not None

    assert resultado.email == "ana@gmail.com"

    assert resultado.kyc_validado is True

    assert (
        usuario_guardado.referencia_kyc
        == "A-1000000001-123"
    )


def test_registro_consulta_el_kyc(
    repositorio,
    solicitud_registro,
    resultado_kyc_aprobado,
):
    provider = FakeProviderKYC(
        resultado_kyc_aprobado
    )

    servicio = ServicioIdentidad(
        repositorio=repositorio,
        provider=provider,
    )

    servicio.registrar_usuario(
        solicitud_registro
    )

    assert len(provider.llamadas) == 1

    request_kyc = provider.llamadas[0]

    assert request_kyc.document_type == "CC"

    assert (
        request_kyc.document_number
        == "1000000001"
    )

    assert request_kyc.full_name == "Ana Perez"


def test_password_no_se_guarda_en_texto_plano(
    repositorio,
    solicitud_registro,
    resultado_kyc_aprobado,
):
    provider = FakeProviderKYC(
        resultado_kyc_aprobado
    )

    servicio = ServicioIdentidad(
        repositorio=repositorio,
        provider=provider,
    )

    servicio.registrar_usuario(
        solicitud_registro
    )

    usuario = repositorio.buscar_por_email(
        "ana@gmail.com"
    )

    assert usuario.password_hash != "Password123!"

    assert servicio.password_hash.verify(
        "Password123!",
        usuario.password_hash,
    )


def test_respuesta_registro_no_expone_password(
    repositorio,
    solicitud_registro,
    resultado_kyc_aprobado,
):
    provider = FakeProviderKYC(
        resultado_kyc_aprobado
    )

    servicio = ServicioIdentidad(
        repositorio=repositorio,
        provider=provider,
    )

    resultado = servicio.registrar_usuario(
        solicitud_registro
    )

    respuesta = resultado.model_dump()

    assert "password" not in respuesta
    assert "password_hash" not in respuesta


def test_no_permite_email_duplicado(
    repositorio,
    solicitud_registro,
    resultado_kyc_aprobado,
):
    provider = FakeProviderKYC(
        resultado_kyc_aprobado
    )

    servicio = ServicioIdentidad(
        repositorio=repositorio,
        provider=provider,
    )

    servicio.registrar_usuario(
        solicitud_registro
    )

    with pytest.raises(
        UsuarioYaExisteError
    ):
        servicio.registrar_usuario(
            solicitud_registro
        )


def test_sin_consentimiento_no_consulta_kyc(
    repositorio,
    solicitud_registro,
    resultado_kyc_aprobado,
):
    solicitud = solicitud_registro.model_copy(
        update={
            "acepta_validacion_identidad": False
        }
    )

    provider = FakeProviderKYC(
        resultado_kyc_aprobado
    )

    servicio = ServicioIdentidad(
        repositorio=repositorio,
        provider=provider,
    )

    with pytest.raises(
        ConsentimientoRequeridoError
    ):
        servicio.registrar_usuario(
            solicitud
        )

    assert provider.llamadas == []

    assert repositorio.usuarios == {}


def test_kyc_rechazado_no_crea_usuario(
    repositorio,
    solicitud_registro,
):
    provider = FakeProviderKYC(
        _resultado_kyc(
            VerificationStatus.REJECTED
        )
    )

    servicio = ServicioIdentidad(
        repositorio=repositorio,
        provider=provider,
    )

    with pytest.raises(
        KYCRechazadoError
    ):
        servicio.registrar_usuario(
            solicitud_registro
        )

    assert repositorio.usuarios == {}


def test_kyc_en_revision_no_crea_usuario(
    repositorio,
    solicitud_registro,
):
    provider = FakeProviderKYC(
        _resultado_kyc(
            VerificationStatus.IN_REVIEW
        )
    )

    servicio = ServicioIdentidad(
        repositorio=repositorio,
        provider=provider,
    )

    with pytest.raises(
        KYCPendienteError
    ):
        servicio.registrar_usuario(
            solicitud_registro
        )

    assert repositorio.usuarios == {}

def test_registro_asigna_rol_cliente(
    repositorio,
    solicitud_registro,
    resultado_kyc_aprobado,
):
    provider = FakeProviderKYC(
        resultado_kyc_aprobado
    )

    servicio = ServicioIdentidad(
        repositorio=repositorio,
        provider=provider,
    )

    resultado = servicio.registrar_usuario(
        solicitud_registro
    )

    assert resultado.rol == Rol.CLIENTE