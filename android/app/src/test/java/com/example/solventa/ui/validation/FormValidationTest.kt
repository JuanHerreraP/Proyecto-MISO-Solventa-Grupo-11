package com.example.solventa.ui.validation

import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Calendar

class FormValidationTest {
    private fun registrationIsValid(
        email: String = "user@example.com",
        selfieCaptured: Boolean = true,
        termsAccepted: Boolean = true
    ) = canSubmitRegistration(
        nombre = "Ana",
        apellido = "Perez",
        tipoDocumento = "CC",
        numeroDocumento = "123456789",
        email = email,
        celular = "3001234567",
        password = "Password123!",
        fechaNacimiento = "1999-01-01",
        termsAccepted = termsAccepted,
        selfieCaptured = selfieCaptured
    )

    @Test
    fun credentialsLoginCanBeSubmittedWhenEmailAndPasswordArePresent() {
        assertTrue(canSubmitCredentialsLogin("user@example.com", "secret"))
    }

    @Test
    fun credentialsLoginCannotBeSubmittedWhenEitherFieldIsBlank() {
        assertFalse(canSubmitCredentialsLogin("", "secret"))
        assertFalse(canSubmitCredentialsLogin("user@example.com", " \t"))
    }

    @Test
    fun registrationCanBeSubmittedWhenRequiredFieldsTermsAndSelfieArePresent() {
        assertTrue(registrationIsValid())
    }

    @Test
    fun registrationRejectsInvalidEmailMissingTermsAndMissingSelfie() {
        assertFalse(registrationIsValid(email = "not-an-email"))
        assertFalse(registrationIsValid(termsAccepted = false))
        assertFalse(registrationIsValid(selfieCaptured = false))
    }

    @Test
    fun nameAcceptsAccentsAndRejectsDigitsOrSymbols() {
        assertNull(errorNombre("María José", "nombres"))
        assertNull(errorNombre("O'Brien-Pérez", "apellidos"))
        assertNotNull(errorNombre("Ana3", "nombres"))
        assertNotNull(errorNombre("A", "nombres"))
        assertNotNull(errorNombre("  ", "nombres"))
    }

    @Test
    fun documentTypeMustBeOneOfTheKnownCodes() {
        assertNull(errorTipoDocumento("CC"))
        assertNull(errorTipoDocumento("PAS"))
        assertNotNull(errorTipoDocumento(""))
        assertNotNull(errorTipoDocumento("cc"))
        assertNotNull(errorTipoDocumento("XX"))
    }

    @Test
    fun documentNumberDependsOnDocumentType() {
        assertNull(errorNumeroDocumento("CC", "123456789"))
        assertNotNull(errorNumeroDocumento("CC", "1234"))
        assertNotNull(errorNumeroDocumento("CC", "12345abc"))
        assertNull(errorNumeroDocumento("PAS", "AB123456"))
        assertNotNull(errorNumeroDocumento("PAS", "AB-12"))
        assertNotNull(errorNumeroDocumento("", "123456789"))
    }

    @Test
    fun mobileNumberNeedsTenDigitsStartingWithThree() {
        assertNull(errorCelular("3001234567"))
        assertNotNull(errorCelular("2001234567"))
        assertNotNull(errorCelular("300123456"))
        assertNotNull(errorCelular("30012345678"))
        assertNotNull(errorCelular(""))
    }

    @Test
    fun passwordNeedsLengthLetterAndDigit() {
        assertNull(errorPassword("Password1"))
        assertNotNull(errorPassword("short1"))
        assertNotNull(errorPassword("12345678"))
        assertNotNull(errorPassword("abcdefgh"))
    }

    @Test
    fun birthDateMustBeIsoPastRealAndAdult() {
        val hoy = Calendar.getInstance().apply { set(2026, Calendar.OCTOBER, 14) }
        assertNull(errorFechaNacimiento("1999-01-01", hoy))
        assertNull(errorFechaNacimiento("2008-10-14", hoy))
        assertNotNull(errorFechaNacimiento("2008-10-15", hoy))
        assertNotNull(errorFechaNacimiento("2030-01-01", hoy))
        assertNotNull(errorFechaNacimiento("1999-02-30", hoy))
        assertNotNull(errorFechaNacimiento("01/01/1999", hoy))
        assertNotNull(errorFechaNacimiento("1890-01-01", hoy))
        assertNotNull(errorFechaNacimiento("", hoy))
    }

    @Test
    fun registrationRejectsMissingRequiredValues() {
        assertFalse(
            canSubmitRegistration(
                nombre = " ",
                apellido = "Perez",
                tipoDocumento = "CC",
                numeroDocumento = "123456789",
                email = "user@example.com",
                celular = "3001234567",
                password = "Password123!",
                fechaNacimiento = "1999-01-01",
                termsAccepted = true,
                selfieCaptured = true
            )
        )
    }
}
