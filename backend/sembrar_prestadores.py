"""Siembra prestadores de asistencia de demostración (HU06).

HU06 no necesita una plataforma para crear prestadores: estos datos ficticios se precargan con
este script idempotente. Si se vuelve a ejecutar, actualiza los mismos prestadores en vez de
duplicarlos. Solo para desarrollo y pruebas; no debe ejecutarse contra producción.

Coordenadas de referencia para la demo (configurar la ubicación del emulador cerca):
  - Bogotá (centro):            latitud 4.7110,  longitud -74.0721
  - Mosquera (Cundinamarca):    latitud 4.7059,  longitud -74.2302

Los prestadores quedan repartidos para mostrar: muy cerca, algo más lejos, en Mosquera, fuera
del radio de 25 km (Medellín) y uno con un servicio incompatible (solo viaje).

Uso:
    python sembrar_prestadores.py
"""


def _prestadores_demo():
    from app.asistencias.modelos import Prestador
    from app.asistencias.modelos import TipoServicioAsistencia as T

    return [
        # --- Dispositivos: cerca del centro de Bogotá ----------------------------------
        Prestador(
            prestador_id="PREST-TEC-001",
            nombre="Solventa Tech Centro",
            direccion="Calle 26 # 13-19, Bogotá (demostración)",
            telefono="3000000001",
            latitud=4.7150,
            longitud=-74.0690,
            servicios=[T.REPARACION_DISPOSITIVO, T.DIAGNOSTICO_TECNICO],
        ),
        Prestador(
            prestador_id="PREST-TEC-002",
            nombre="TechCare Norte",
            direccion="Autopista Norte # 100-40, Bogotá (demostración)",
            telefono="3000000002",
            latitud=4.6860,
            longitud=-74.0480,
            servicios=[T.REPARACION_DISPOSITIVO],
        ),
        # --- Dispositivos: en Mosquera (dentro del radio por defecto, ~17-18 km) --------
        Prestador(
            prestador_id="PREST-TEC-003",
            nombre="Mosquera Dispositivos",
            direccion="Carrera 3 # 15-20, Mosquera (demostración)",
            telefono="3000000003",
            latitud=4.7059,
            longitud=-74.2302,
            servicios=[T.DIAGNOSTICO_TECNICO, T.REPARACION_DISPOSITIVO],
        ),
        # --- Dispositivos: fuera del radio de 25 km (Medellín) --------------------------
        Prestador(
            prestador_id="PREST-TEC-004",
            nombre="Lejos Tech Medellín",
            direccion="Carrera 70 # 45-10, Medellín (demostración)",
            telefono="3000000004",
            latitud=6.2518,
            longitud=-75.5636,
            servicios=[T.REPARACION_DISPOSITIVO],
        ),
        # --- Dispositivos: inactivo (no debe aparecer nunca) ----------------------------
        Prestador(
            prestador_id="PREST-TEC-005",
            nombre="Inactivo Tech",
            direccion="Calle 72 # 10-07, Bogotá (demostración)",
            telefono="3000000005",
            latitud=4.7130,
            longitud=-74.0700,
            servicios=[T.REPARACION_DISPOSITIVO, T.DIAGNOSTICO_TECNICO],
            activo=False,
        ),
        # --- Viaje: cerca del centro de Bogotá ------------------------------------------
        Prestador(
            prestador_id="PREST-VIA-001",
            nombre="Centro Médico Aliado",
            direccion="Calle 45 # 20-15, Bogotá (demostración)",
            telefono="3000000011",
            latitud=4.7120,
            longitud=-74.0660,
            servicios=[T.ASISTENCIA_MEDICA],
        ),
        Prestador(
            prestador_id="PREST-VIA-002",
            nombre="Asistencia Viajero 24/7",
            direccion="Av. El Dorado # 68-30, Bogotá (demostración)",
            telefono="3000000012",
            latitud=4.6980,
            longitud=-74.1050,
            servicios=[T.ASISTENCIA_VIAJERO, T.ASISTENCIA_MEDICA],
        ),
        # --- Viaje: en Mosquera ---------------------------------------------------------
        Prestador(
            prestador_id="PREST-VIA-003",
            nombre="Mosquera Salud Viajero",
            direccion="Calle 2 # 4-33, Mosquera (demostración)",
            telefono="3000000013",
            latitud=4.7090,
            longitud=-74.2250,
            servicios=[T.ASISTENCIA_VIAJERO],
        ),
        # --- En Madrid (Cundinamarca): junto a Mosquera, occidente de la Sabana ---------
        Prestador(
            prestador_id="PREST-MAD-001",
            nombre="Solventa Asistencia Madrid",
            direccion="Calle 7 # 5-20, Madrid (demostración)",
            telefono="3000000021",
            latitud=4.7328,
            longitud=-74.2635,
            servicios=[
                T.REPARACION_DISPOSITIVO,
                T.DIAGNOSTICO_TECNICO,
                T.ASISTENCIA_MEDICA,
            ],
        ),
        Prestador(
            prestador_id="PREST-MAD-002",
            nombre="Centro Técnico Madrid",
            direccion="Carrera 6 # 8-14, Madrid (demostración)",
            telefono="3000000022",
            latitud=4.7285,
            longitud=-74.2710,
            servicios=[T.DIAGNOSTICO_TECNICO, T.REPARACION_DISPOSITIVO],
        ),
        Prestador(
            prestador_id="PREST-MAD-003",
            nombre="Asistencia Occidente",
            direccion="Calle 10 # 3-45, Madrid (demostración)",
            telefono="3000000023",
            latitud=4.7410,
            longitud=-74.2550,
            servicios=[T.ASISTENCIA_VIAJERO, T.ASISTENCIA_MEDICA],
        ),
        # --- En el centro de Bogotá -----------------------------------------------------
        Prestador(
            prestador_id="PREST-BOG-001",
            nombre="Solventa Bogotá Centro",
            direccion="Carrera 7 # 12-30, Bogotá (demostración)",
            telefono="3000000031",
            latitud=4.7115,
            longitud=-74.0700,
            servicios=[
                T.REPARACION_DISPOSITIVO,
                T.DIAGNOSTICO_TECNICO,
                T.ASISTENCIA_MEDICA,
            ],
        ),
        Prestador(
            prestador_id="PREST-BOG-002",
            nombre="Centro Médico Bogotá",
            direccion="Calle 13 # 9-18, Bogotá (demostración)",
            telefono="3000000032",
            latitud=4.7180,
            longitud=-74.0660,
            servicios=[T.ASISTENCIA_MEDICA, T.ASISTENCIA_VIAJERO],
        ),
        Prestador(
            prestador_id="PREST-BOG-003",
            nombre="TechCare Bogotá",
            direccion="Carrera 10 # 20-05, Bogotá (demostración)",
            telefono="3000000033",
            latitud=4.7000,
            longitud=-74.0800,
            servicios=[T.REPARACION_DISPOSITIVO, T.DIAGNOSTICO_TECNICO],
        ),
    ]


def main() -> int:
    from app.asistencias import modelos_db  # noqa: F401
    from app.asistencias.repositorio import RepositorioPrestadoresPostgres
    from app.infraestructura.database import (
        Base,
        SessionLocal,
        engine,
        esperar_base_disponible,
        preparar_esquema_registro,
    )

    esperar_base_disponible()
    Base.metadata.create_all(bind=engine)
    preparar_esquema_registro()

    db = SessionLocal()
    try:
        repositorio = RepositorioPrestadoresPostgres(db)
        prestadores = _prestadores_demo()
        for prestador in prestadores:
            repositorio.guardar(prestador)
            estado = "activo" if prestador.activo else "INACTIVO"
            servicios = ", ".join(s.value for s in prestador.servicios)
            print(f"{prestador.prestador_id:<14} {prestador.nombre:<26} {estado:<8} {servicios}")
        print(f"{len(prestadores)} prestadores de demostración listos.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
