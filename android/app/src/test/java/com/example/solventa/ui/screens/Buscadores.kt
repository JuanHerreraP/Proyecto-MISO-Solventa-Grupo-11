package com.example.solventa.ui.screens

import androidx.compose.ui.test.SemanticsNodeInteraction
import androidx.compose.ui.test.SemanticsNodeInteractionsProvider
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.hasText

/** Botón o enlace con ese texto (descarta títulos con el mismo texto que no son clicables). */
fun SemanticsNodeInteractionsProvider.boton(texto: String, substring: Boolean = false): SemanticsNodeInteraction =
    onNode(hasText(texto, substring = substring) and hasClickAction())

/** Campo de texto por su etiqueta; SolventaTextField la muestra en mayúsculas. */
fun SemanticsNodeInteractionsProvider.campo(etiqueta: String): SemanticsNodeInteraction =
    onNode(hasSetTextAction() and hasText(etiqueta.uppercase(), substring = true))
