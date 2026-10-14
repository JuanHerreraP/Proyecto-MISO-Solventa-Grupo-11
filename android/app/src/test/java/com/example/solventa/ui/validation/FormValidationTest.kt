package com.example.solventa.ui.validation

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

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
