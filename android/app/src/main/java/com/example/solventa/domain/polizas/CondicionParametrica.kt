package com.example.solventa.domain.polizas

/**
 * La condición paramétrica de una póliza llega en `descripcion_cobertura` como pares
 * `clave=valor` separados por `;`, por ejemplo:
 *
 *   "tipo_evento=RETRASO_VUELO; numero_vuelo=AV123; ubicacion=BOG; umbral_disparo=180; unidad=MINUTOS"
 *
 * Este objeto la convierte en una lista de filas legibles (etiqueta + valor) para mostrarlas en el
 * certificado. Solo se incluyen los campos que vienen con valor.
 */
object CondicionParametrica {

    /** Una fila lista para pintar: etiqueta amigable, su valor y si debe formatearse como dinero. */
    data class Campo(val etiqueta: String, val valor: String, val esMoneda: Boolean = false)

    // `tipo_evento` no se muestra: ya se refleja en el nombre de la cobertura ("Retraso de
    // vuelo" / "Evento climático"), así que incluirlo duplicaría la información en el certificado.
    private val ETIQUETAS = linkedMapOf(
        "numero_vuelo" to "Número de vuelo",
        "ubicacion" to "Ubicación",
        "parametro" to "Parámetro",
        "umbral_disparo" to "Umbral de activación",
        "unidad" to "Unidad",
        "valor_asegurado" to "Valor asegurado"
    )

    /** Campos que representan dinero y deben formatearse con la moneda de la póliza. */
    private val MONEDA = setOf("valor_asegurado")

    private val VALORES = mapOf(
        "RETRASO_VUELO" to "Retraso de vuelo",
        "EVENTO_CLIMATICO" to "Evento climático",
        "PRECIPITACION" to "Precipitación",
        "MINUTOS" to "minutos",
        "MM" to "mm"
    )

    /** Pares crudos `clave=valor`. Tolera espacios, vacíos y claves repetidas (gana la última). */
    fun parsear(descripcion: String?): Map<String, String> {
        if (descripcion.isNullOrBlank()) return emptyMap()
        val resultado = linkedMapOf<String, String>()
        for (parte in descripcion.split(";")) {
            val idx = parte.indexOf('=')
            if (idx <= 0) continue
            val clave = parte.substring(0, idx).trim().lowercase()
            val valor = parte.substring(idx + 1).trim()
            if (clave.isNotEmpty() && valor.isNotEmpty()) resultado[clave] = valor
        }
        return resultado
    }

    /**
     * Filas legibles de la condición, en un orden estable. Los campos conocidos van primero con su
     * etiqueta amigable; cualquier campo extra con valor se agrega al final con su clave formateada.
     */
    fun campos(descripcion: String?): List<Campo> {
        val crudos = parsear(descripcion).toMutableMap()
        // tipo_evento no se pinta (redundante con el nombre de la cobertura).
        crudos.remove("tipo_evento")
        val filas = mutableListOf<Campo>()
        for ((clave, etiqueta) in ETIQUETAS) {
            val valor = crudos.remove(clave) ?: continue
            filas += Campo(etiqueta, humanizarValor(valor), esMoneda = clave in MONEDA)
        }
        // Campos no previstos pero presentes: no se pierden.
        for ((clave, valor) in crudos) {
            filas += Campo(humanizarClave(clave), humanizarValor(valor))
        }
        return filas
    }

    private fun humanizarValor(valor: String): String = VALORES[valor] ?: valor

    private fun humanizarClave(clave: String): String =
        clave.replace('_', ' ').replaceFirstChar { it.uppercase() }
}
