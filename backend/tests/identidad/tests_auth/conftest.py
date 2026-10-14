from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.identidad.modelos import (
    SolicitudRegistro,
    VerificationResult,
    VerificationStatus,
)


class FakeRepositorioUsuarios:
    """Repositorio en memoria exclusivo para pruebas unitarias."""

    def __init__(self):
        self.usuarios = {}

    def buscar_por_email(self, email: str):
        return self.usuarios.get(email.strip().lower())

    def buscar_por_documento(self, tipo_documento: str, numero_documento: str):
        return next(
            (
                usuario
                for usuario in self.usuarios.values()
                if usuario.tipo_documento == tipo_documento.strip().upper()
                and usuario.numero_documento == numero_documento.strip().upper()
            ),
            None,
        )

    def guardar(self, usuario):
        if usuario.id is None:
            usuario.id = uuid4()

        if usuario.fecha_creacion is None:
            usuario.fecha_creacion = datetime.now(timezone.utc)

        self.usuarios[usuario.email.strip().lower()] = usuario

        return usuario


class FakeProviderKYC:
    """Proveedor KYC controlado por la prueba."""

    def __init__(self, resultado):
        self.resultado = resultado
        self.llamadas = []

    def verify(self, request):
        self.llamadas.append(request)
        return self.resultado


@pytest.fixture
def repositorio():
    return FakeRepositorioUsuarios()


@pytest.fixture
def solicitud_registro():
    return SolicitudRegistro(
        nombre="Ana",
        apellido="Perez",
        email="ana@gmail.com",
        password="Password123!",
        tipo_documento="CC",
        numero_documento="1000000001",
        fecha_nacimiento="1999-01-01",
        celular="3001234567",
        acepta_validacion_identidad=True,
        selfie_base64="/9j/2Q==",
    )


@pytest.fixture
def resultado_kyc_aprobado():
    return VerificationResult(
        verification_id="A-1000000001-123",
        status=VerificationStatus.APPROVED,
        risk_score=0.15,
        provider_name="proveedor-kyc-a",
        checked_at=datetime.now(timezone.utc),
    )
