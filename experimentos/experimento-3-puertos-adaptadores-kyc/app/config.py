import os


def get_configured_provider_name() -> str:
    """
    Único punto de configuración externo del experimento: qué proveedor KYC
    está detrás del puerto en este momento. En el experimento se cambia con
    la variable de entorno KYC_PROVIDER; en un despliegue real correspondería
    a configuración/infraestructura (p. ej. un parámetro en AWS), nunca a un
    cambio de código en el servicio de Identidad.
    """
    return os.getenv("KYC_PROVIDER", "A").strip().upper()
