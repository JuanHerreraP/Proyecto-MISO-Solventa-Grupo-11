"""Modelos del dominio de identidad."""

from dataclasses import dataclass

from enum import Enum
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class Rol(str, Enum):
    ASESOR_VENTAS = "ASESOR_VENTAS"
    ANALISTA_RIESGOS = "ANALISTA_RIESGOS"
    OPERACIONES_SINIESTROS = "OPERACIONES_SINIESTROS"
    SOCIO_DISTRIBUCION = "SOCIO_DISTRIBUCION"
    CLIENTE = "CLIENTE"
    SERVICIO_INTERNO = "SERVICIO_INTERNO"


class VerificationStatus(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IN_REVIEW = "IN_REVIEW"


@dataclass(frozen=True)
class VerificationRequest:
    customer_id: str
    consent_id: str
    document_type: str
    document_number: str
    full_name: str
    birth_date: date


@dataclass(frozen=True)
class VerificationResult:
    verification_id: str
    status: VerificationStatus
    # Riesgo normalizado 0.0 (bajo riesgo) - 1.0 (alto riesgo). La semántica de
    # "riesgo" (y no de "confianza" o "score" crudo del proveedor) es una
    # decisión del dominio: cada adaptador debe traducir a esta semántica.
    risk_score: float
    provider_name: str
    checked_at: datetime


class SolicitudRegistro(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    apellido: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    tipo_documento: str
    numero_documento: str
    fecha_nacimiento: date
    acepta_validacion_identidad: bool


class Usuario(BaseModel):
    id: str
    nombre: str
    apellido: str
    email: EmailStr
    password_hash: str
    rol: Rol
    activo: bool
    kyc_validado: bool
    referencia_kyc: str | None = None
    fecha_creacion: datetime
    consentimiento_kyc: bool

class RespuestaRegistro(BaseModel):
    id: str
    nombre: str
    apellido: str
    email: EmailStr
    rol: Rol
    kyc_validado: bool
    fecha_creacion: datetime


class SolicitudLogin(BaseModel):
    email: EmailStr
    password: str


class RespuestaLogin(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int