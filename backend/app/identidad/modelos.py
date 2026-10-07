"""Modelos del dominio de identidad."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class Rol(str, Enum):
    ASESOR_VENTAS = "ASESOR_VENTAS"
    ANALISTA_RIESGOS = "ANALISTA_RIESGOS"
    OPERACIONES_SINIESTROS = "OPERACIONES_SINIESTROS"
    SOCIO_DISTRIBUCION = "SOCIO_DISTRIBUCION"
    CLIENTE = "CLIENTE"
    SERVICIO_INTERNO = "SERVICIO_INTERNO"


class EstadoKYC(str, Enum):
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"


class SolicitudRegistro(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    apellido: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    tipo_documento: str = Field(min_length=1, max_length=20)
    numero_documento: str = Field(min_length=5, max_length=30)


class SolicitudKYC(BaseModel):
    nombre: str
    apellido: str
    tipo_documento: str
    numero_documento: str


class ResultadoKYC(BaseModel):
    estado: EstadoKYC
    referencia: str
    motivo: str | None = None


class Usuario(BaseModel):
    id: str
    nombre: str
    apellido: str
    email: EmailStr
    password_hash: str
    rol: Rol
    activo: bool
    kyc_validado: bool
    referencia_kyc: str
    fecha_creacion: datetime


class RespuestaRegistro(BaseModel):
    id: str
    nombre: str
    apellido: str
    email: EmailStr
    rol: Rol
    kyc_validado: bool
    fecha_creacion: datetime