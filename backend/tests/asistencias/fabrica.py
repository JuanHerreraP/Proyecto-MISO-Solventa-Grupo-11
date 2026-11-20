"""Fábricas de prueba para la asistencia en sitio (HU06)."""

from app.asistencias.modelos import Prestador, TipoServicioAsistencia

# Centro de Bogotá y Mosquera, usados como referencia en las pruebas.
BOGOTA = (4.7110, -74.0721)
MOSQUERA = (4.7059, -74.2302)
MEDELLIN = (6.2518, -75.5636)


def prestador(**cambios) -> Prestador:
    datos = {
        "prestador_id": "PREST-TEC-001",
        "nombre": "Solventa Tech Centro",
        "direccion": "Calle 26 # 13-19, Bogotá (demostración)",
        "telefono": "3000000001",
        "latitud": 4.7150,
        "longitud": -74.0690,
        "servicios": [
            TipoServicioAsistencia.REPARACION_DISPOSITIVO,
            TipoServicioAsistencia.DIAGNOSTICO_TECNICO,
        ],
        "activo": True,
    }
    datos.update(cambios)
    return Prestador(**datos)
