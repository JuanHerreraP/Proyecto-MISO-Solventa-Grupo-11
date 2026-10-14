package com.example.solventa.data.session

import android.content.Context
import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyPermanentlyInvalidatedException
import android.security.keystore.KeyProperties
import android.security.keystore.UserNotAuthenticatedException
import android.util.Base64
import com.example.solventa.domain.auth.AutenticacionVencidaException
import com.example.solventa.domain.auth.BovedaSesion
import com.example.solventa.domain.auth.LlaveInvalidadaException
import java.security.GeneralSecurityException
import java.security.KeyStore
import javax.crypto.AEADBadTagException
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Guarda el refresh token cifrado con AES-256-GCM. La llave vive en el Android Keystore,
 * no se puede extraer y solo se puede usar durante [VENTANA_SEGUNDOS] después de una
 * autenticación biométrica fuerte. Si se registra una huella nueva, la llave se invalida.
 *
 * Solo se guarda el texto cifrado y el vector de inicialización; el token en claro nunca
 * toca el disco.
 */
class KeystoreBovedaSesion(context: Context) : BovedaSesion {

    private val preferencias =
        context.applicationContext.getSharedPreferences(ARCHIVO, Context.MODE_PRIVATE)

    private val keyStore: KeyStore = KeyStore.getInstance(PROVEEDOR).apply { load(null) }

    override fun tieneSesionGuardada(): Boolean =
        preferencias.contains(CLAVE_DATOS) && preferencias.contains(CLAVE_IV) && llaveExistente() != null

    override fun preparar() {
        if (llaveExistente() == null) crearLlave()
    }

    override fun guardar(refreshToken: String) {
        val llave = llaveExistente() ?: crearLlave()
        val cifrador = Cipher.getInstance(TRANSFORMACION)
        iniciar { cifrador.init(Cipher.ENCRYPT_MODE, llave) }
        val cifrado = finalizar { cifrador.doFinal(refreshToken.toByteArray(Charsets.UTF_8)) }

        preferencias.edit()
            .putString(CLAVE_DATOS, Base64.encodeToString(cifrado, Base64.NO_WRAP))
            .putString(CLAVE_IV, Base64.encodeToString(cifrador.iv, Base64.NO_WRAP))
            .apply()
    }

    override fun leer(): String {
        val datos = preferencias.getString(CLAVE_DATOS, null)
        val iv = preferencias.getString(CLAVE_IV, null)
        val llave = llaveExistente()
        if (datos == null || iv == null || llave == null) {
            borrar()
            throw LlaveInvalidadaException()
        }

        val cifrador = Cipher.getInstance(TRANSFORMACION)
        iniciar {
            cifrador.init(
                Cipher.DECRYPT_MODE,
                llave,
                GCMParameterSpec(BITS_ETIQUETA, Base64.decode(iv, Base64.NO_WRAP))
            )
        }
        val claro = finalizar { cifrador.doFinal(Base64.decode(datos, Base64.NO_WRAP)) }
        return String(claro, Charsets.UTF_8)
    }

    override fun borrar() {
        preferencias.edit().clear().apply()
        if (keyStore.containsAlias(ALIAS)) keyStore.deleteEntry(ALIAS)
    }

    private inline fun iniciar(bloque: () -> Unit) {
        try {
            bloque()
        } catch (error: KeyPermanentlyInvalidatedException) {
            borrar()
            throw LlaveInvalidadaException(error)
        } catch (error: UserNotAuthenticatedException) {
            throw AutenticacionVencidaException(error)
        }
    }

    private inline fun finalizar(bloque: () -> ByteArray): ByteArray = try {
        bloque()
    } catch (error: AEADBadTagException) {
        // Datos alterados o cifrados con otra llave.
        borrar()
        throw LlaveInvalidadaException(error)
    } catch (error: GeneralSecurityException) {
        // Algunos dispositivos reportan así que la ventana de autenticación pasó.
        throw AutenticacionVencidaException(error)
    }

    private fun llaveExistente(): SecretKey? =
        (keyStore.getEntry(ALIAS, null) as? KeyStore.SecretKeyEntry)?.secretKey

    private fun crearLlave(): SecretKey {
        val especificacion = KeyGenParameterSpec.Builder(
            ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .setUserAuthenticationRequired(true)
            .setInvalidatedByBiometricEnrollment(true)
            .apply {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                    setUserAuthenticationParameters(
                        VENTANA_SEGUNDOS,
                        KeyProperties.AUTH_BIOMETRIC_STRONG
                    )
                } else {
                    @Suppress("DEPRECATION")
                    setUserAuthenticationValidityDurationSeconds(VENTANA_SEGUNDOS)
                }
            }
            .build()

        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, PROVEEDOR)
            .apply { init(especificacion) }
            .generateKey()
    }

    private companion object {
        const val PROVEEDOR = "AndroidKeyStore"
        const val ALIAS = "solventa_sesion_biometrica"
        const val ARCHIVO = "solventa_sesion"
        const val CLAVE_DATOS = "refresh_cifrado"
        const val CLAVE_IV = "refresh_iv"
        const val TRANSFORMACION = "AES/GCM/NoPadding"
        const val BITS_ETIQUETA = 128

        /** Tiempo para leer, renovar y volver a guardar el token tras validar la huella. */
        const val VENTANA_SEGUNDOS = 30
    }
}
