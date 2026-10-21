package com.example.solventa.domain.cotizaciones

enum class TipoCampoCotizacion { TEXTO, ENTERO, DECIMAL, FECHA, BOOLEANO, OPCION }

data class CampoCotizacion(
    val codigo: String,
    val etiqueta: String,
    val tipo: TipoCampoCotizacion,
    val requerido: Boolean = true,
    val descripcion: String,
    val unidad: String? = null,
    val opciones: List<String> = emptyList()
)

data class DefinicionRamoCotizacion(
    val ramo: RamoCotizacion,
    val tituloFormulario: String,
    val descripcionFormulario: String,
    val campos: List<CampoCotizacion>
)

/**
 * Catálogo local compatible con GET /api/v1/cotizaciones/ramos.
 * En la integración remota las mismas definiciones serán provistas por el backend.
 */
object CatalogoCotizaciones {
    private val definiciones = listOf(
        DefinicionRamoCotizacion(
            ramo = RamoCotizacion.VIAJE,
            tituloFormulario = "Datos de tu viaje",
            descripcionFormulario = "Completa la información necesaria para proteger tu recorrido.",
            campos = listOf(
                campo("destino", "Destino", TipoCampoCotizacion.TEXTO, "País o ciudad principal"),
                campo("fecha_inicio", "Fecha de salida", TipoCampoCotizacion.FECHA, "Inicio de la cobertura"),
                campo("fecha_fin", "Fecha de regreso", TipoCampoCotizacion.FECHA, "Fin de la cobertura"),
                campo("numero_viajeros", "Número de viajeros", TipoCampoCotizacion.ENTERO, "Personas cubiertas"),
                campo(
                    "valor_asegurado",
                    "Valor asegurado",
                    TipoCampoCotizacion.DECIMAL,
                    "Monto máximo de protección",
                    unidad = "COP"
                )
            )
        ),
        DefinicionRamoCotizacion(
            ramo = RamoCotizacion.DISPOSITIVOS,
            tituloFormulario = "Datos de tu dispositivo",
            descripcionFormulario = "Cuéntanos qué equipo quieres proteger.",
            campos = listOf(
                campo(
                    "tipo_dispositivo",
                    "Tipo de dispositivo",
                    TipoCampoCotizacion.OPCION,
                    "Selecciona la clase de equipo",
                    opciones = listOf("CELULAR", "TABLETA", "PORTATIL")
                ),
                campo("marca", "Marca", TipoCampoCotizacion.TEXTO, "Fabricante del dispositivo"),
                campo("modelo", "Modelo", TipoCampoCotizacion.TEXTO, "Referencia comercial"),
                campo(
                    "valor_dispositivo",
                    "Valor del dispositivo",
                    TipoCampoCotizacion.DECIMAL,
                    "Valor comercial declarado",
                    unidad = "COP"
                ),
                campo("fecha_compra", "Fecha de compra", TipoCampoCotizacion.FECHA, "Fecha de adquisición"),
                campo(
                    "meses_cobertura",
                    "Meses de cobertura",
                    TipoCampoCotizacion.ENTERO,
                    "Duración de la protección",
                    unidad = "meses"
                )
            )
        ),
        DefinicionRamoCotizacion(
            ramo = RamoCotizacion.VIDA,
            tituloFormulario = "Datos de la protección",
            descripcionFormulario = "Completa la información de la persona que estará asegurada.",
            campos = listOf(
                campo(
                    "fecha_nacimiento",
                    "Fecha de nacimiento",
                    TipoCampoCotizacion.FECHA,
                    "Fecha de nacimiento de la persona asegurada"
                ),
                campo(
                    "valor_asegurado",
                    "Valor asegurado",
                    TipoCampoCotizacion.DECIMAL,
                    "Monto de protección solicitado",
                    unidad = "COP"
                ),
                campo(
                    "meses_cobertura",
                    "Meses de cobertura",
                    TipoCampoCotizacion.ENTERO,
                    "Duración de la protección",
                    unidad = "meses"
                ),
                campo("fumador", "¿Es fumador?", TipoCampoCotizacion.BOOLEANO, "Consumo de tabaco")
            )
        ),
        DefinicionRamoCotizacion(
            ramo = RamoCotizacion.PARAMETRICO,
            tituloFormulario = "Datos del evento",
            descripcionFormulario = "Define la condición objetiva que activará la protección.",
            campos = listOf(
                campo(
                    "tipo_evento",
                    "Tipo de evento",
                    TipoCampoCotizacion.OPCION,
                    "Evento que activará la cobertura",
                    opciones = listOf("RETRASO_VUELO", "EVENTO_CLIMATICO")
                ),
                campo("fecha_inicio", "Fecha de inicio", TipoCampoCotizacion.FECHA, "Inicio de observación"),
                campo("fecha_fin", "Fecha de finalización", TipoCampoCotizacion.FECHA, "Fin de observación"),
                campo(
                    "umbral_disparo",
                    "Umbral de activación",
                    TipoCampoCotizacion.DECIMAL,
                    "Valor que activa la cobertura"
                ),
                campo(
                    "valor_asegurado",
                    "Valor asegurado",
                    TipoCampoCotizacion.DECIMAL,
                    "Monto pagadero al cumplirse la condición",
                    unidad = "COP"
                ),
                campo(
                    "numero_vuelo",
                    "Número de vuelo",
                    TipoCampoCotizacion.TEXTO,
                    "Requerido para retrasos de vuelo",
                    requerido = false
                ),
                campo(
                    "ubicacion",
                    "Ubicación",
                    TipoCampoCotizacion.TEXTO,
                    "Requerida para eventos climáticos",
                    requerido = false
                )
            )
        )
    ).associateBy { it.ramo }

    fun definicion(ramo: RamoCotizacion): DefinicionRamoCotizacion =
        requireNotNull(definiciones[ramo]) { "Ramo sin definición: $ramo" }

    private fun campo(
        codigo: String,
        etiqueta: String,
        tipo: TipoCampoCotizacion,
        descripcion: String,
        requerido: Boolean = true,
        unidad: String? = null,
        opciones: List<String> = emptyList()
    ) = CampoCotizacion(
        codigo = codigo,
        etiqueta = etiqueta,
        tipo = tipo,
        requerido = requerido,
        descripcion = descripcion,
        unidad = unidad,
        opciones = opciones
    )
}
