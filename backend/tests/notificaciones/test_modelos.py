"""Modelos de notificaciones: grupo, lectura y validaciones."""

import pytest
from pydantic import ValidationError

from app.notificaciones.modelos import grupo_de
from tests.notificaciones.fabrica import AHORA, HOY, dispositivo, notificacion


def test_el_grupo_de_una_notificacion_es_su_tipo_y_su_dia() -> None:
    n = notificacion(1)

    assert n.grupo == grupo_de(n.tipo, HOY) == "ESTADO_SINIESTRO:2026-12-10"


def test_una_notificacion_esta_leida_cuando_tiene_fecha_de_lectura() -> None:
    assert notificacion(1).leida is False
    assert notificacion(1, leida_en=AHORA).leida is True


def test_no_acepta_titulos_ni_tokens_vacios_o_demasiado_largos() -> None:
    with pytest.raises(ValidationError):
        notificacion(1, titulo="")
    with pytest.raises(ValidationError):
        notificacion(1, cuerpo="x" * 401)
    with pytest.raises(ValidationError):
        dispositivo("")
    with pytest.raises(ValidationError):
        dispositivo("t" * 513)
