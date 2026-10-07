from app.perfilamiento.dominio.modelos import SenalesPerfilamiento


def senales(
    comportamiento_pago: float = 0.9,
    nivel_endeudamiento: float = 0.2,
    estabilidad: float = 0.9,
    riesgo_zona: str = "BAJO",
    consentimiento_vigente: bool = True,
    cliente_id: str = "CLI-001",
) -> SenalesPerfilamiento:
    return SenalesPerfilamiento(
        cliente_id=cliente_id,
        consentimiento_id="CONS-001",
        consentimiento_vigente=consentimiento_vigente,
        open_finance={
            "comportamiento_pago": comportamiento_pago,
            "nivel_endeudamiento": nivel_endeudamiento,
        },
        open_data={"estabilidad": estabilidad, "riesgo_zona": riesgo_zona},
    )
