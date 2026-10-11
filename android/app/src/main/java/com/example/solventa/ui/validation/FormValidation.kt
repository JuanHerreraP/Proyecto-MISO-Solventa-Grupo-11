package com.example.solventa.ui.validation

fun canSubmitCredentialsLogin(email: String, password: String): Boolean =
    email.isNotBlank() && password.isNotBlank()

fun canSubmitRegistration(
    email: String,
    password: String,
    termsAccepted: Boolean
): Boolean = termsAccepted && email.isNotBlank() && password.isNotBlank()
