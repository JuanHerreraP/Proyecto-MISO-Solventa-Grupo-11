package com.example.solventa.ui.validation

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class FormValidationTest {
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
    fun registrationCanBeSubmittedWhenRequiredFieldsAndTermsArePresent() {
        assertTrue(canSubmitRegistration("user@example.com", "secret", termsAccepted = true))
    }

    @Test
    fun registrationCannotBeSubmittedWhenRequiredFieldIsBlankOrTermsAreNotAccepted() {
        assertFalse(canSubmitRegistration("", "secret", termsAccepted = true))
        assertFalse(canSubmitRegistration("user@example.com", " ", termsAccepted = true))
        assertFalse(canSubmitRegistration("user@example.com", "secret", termsAccepted = false))
    }
}
