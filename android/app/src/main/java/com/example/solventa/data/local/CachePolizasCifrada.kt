package com.example.solventa.data.local

import android.content.Context
import android.content.SharedPreferences
import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import com.example.solventa.domain.polizas.Billetera
import com.example.solventa.domain.polizas.BilleteraCacheada
import com.example.solventa.domain.polizas.CachePolizas
import com.example.solventa.domain.polizas.Certificado
import com.example.solventa.domain.polizas.CertificadoCacheado
import com.example.solventa.domain.polizas.ClaveUsuarioCache
import com.example.solventa.domain.polizas.MetadatosSincronizacion
import com.google.gson.Gson
import java.io.IOException
import java.security.GeneralSecurityException
import java.security.KeyStore
import java.security.MessageDigest
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Caché de la billetera cifrada con AES-256-GCM.
 *
 * La llave no sale del Android Keystore y el identificador del usuario se usa como dato
 * autenticado adicional. Alterar o intercambiar los datos cifrados invalida la instantánea.
 */
class CachePolizasCifrada private constructor(
    private val almacen: AlmacenCachePolizas,
    private val cifrador: CifradorCachePolizas,
    private val gson: Gson
) : CachePolizas {

    constructor(context: Context) : this(
        almacen = PreferenciasCachePolizas(
            context.applicationContext.getSharedPreferences(ARCHIVO, Context.MODE_PRIVATE)
        ),
        cifrador = CifradorCachePolizas(ProveedorLlaveKeystore()),
        gson = Gson()
    )

    internal constructor(
        almacen: AlmacenCachePolizas,
        llave: SecretKey
    ) : this(
        almacen = almacen,
        cifrador = CifradorCachePolizas(ProveedorLlaveFija(llave)),
        gson = Gson()
    )

    override suspend fun reemplazar(
        usuario: ClaveUsuarioCache,
        billetera: Billetera,
        certificados: List<Certificado>,
        sincronizadaEnMs: Long
    ) {
        require(sincronizadaEnMs >= 0) { "La fecha de sincronización no puede ser negativa." }
        val polizas = billetera.polizas.mapTo(mutableSetOf()) { it.polizaId }
        require(certificados.all { it.polizaId in polizas }) {
            "No se puede guardar un certificado que no pertenezca a la billetera."
        }

        val instantanea = InstantaneaPersistida(
            version = VERSION,
            usuarioId = usuario.valor,
            billetera = billetera,
            certificados = certificados.distinctBy { it.polizaId },
            sincronizadaEnMs = sincronizadaEnMs
        )
        val cifrado = cifrador.cifrar(gson.toJson(instantanea), aad(usuario))
        almacen.guardar(claveAlmacen(usuario), gson.toJson(cifrado))
    }

    override suspend fun billetera(usuario: ClaveUsuarioCache): BilleteraCacheada? {
        val instantanea = leer(usuario) ?: return null
        return BilleteraCacheada(
            billetera = instantanea.billetera,
            metadatos = instantanea.metadatos(usuario)
        )
    }

    override suspend fun certificado(
        usuario: ClaveUsuarioCache,
        polizaId: String
    ): CertificadoCacheado? {
        val instantanea = leer(usuario) ?: return null
        val certificado = instantanea.certificados.firstOrNull { it.polizaId == polizaId }
            ?: return null
        return CertificadoCacheado(
            certificado = certificado,
            metadatos = instantanea.metadatos(usuario)
        )
    }

    override suspend fun eliminar(usuario: ClaveUsuarioCache) {
        almacen.eliminar(claveAlmacen(usuario))
    }

    override suspend fun eliminarTodo() {
        almacen.eliminarTodo()
        cifrador.eliminarLlave()
    }

    private fun leer(usuario: ClaveUsuarioCache): InstantaneaPersistida? {
        val clave = claveAlmacen(usuario)
        val guardado = almacen.leer(clave) ?: return null
        return try {
            val sobre = gson.fromJson(guardado, ContenidoCifrado::class.java)
            val claro = cifrador.descifrar(sobre, aad(usuario))
            gson.fromJson(claro, InstantaneaPersistida::class.java)
                .takeIf {
                    it.version == VERSION &&
                        it.usuarioId == usuario.valor &&
                        it.sincronizadaEnMs >= 0
                }
                ?: error("La instantánea no pertenece al usuario o tiene una versión inválida.")
        } catch (error: Exception) {
            almacen.eliminar(clave)
            null
        }
    }

    private fun aad(usuario: ClaveUsuarioCache): ByteArray =
        "$VERSION:${usuario.valor}".toByteArray(Charsets.UTF_8)

    private fun claveAlmacen(usuario: ClaveUsuarioCache): String =
        MessageDigest.getInstance("SHA-256")
            .digest(usuario.valor.toByteArray(Charsets.UTF_8))
            .aHex()

    private fun InstantaneaPersistida.metadatos(usuario: ClaveUsuarioCache) =
        MetadatosSincronizacion(usuario, sincronizadaEnMs)

    private data class InstantaneaPersistida(
        val version: Int,
        val usuarioId: String,
        val billetera: Billetera,
        val certificados: List<Certificado>,
        val sincronizadaEnMs: Long
    )

    private companion object {
        const val ARCHIVO = "solventa_polizas_cifradas"
        const val VERSION = 1
    }
}

internal interface AlmacenCachePolizas {
    fun guardar(clave: String, valor: String)
    fun leer(clave: String): String?
    fun eliminar(clave: String)
    fun eliminarTodo()
}

private class PreferenciasCachePolizas(
    private val preferencias: SharedPreferences
) : AlmacenCachePolizas {
    override fun guardar(clave: String, valor: String) {
        if (!preferencias.edit().putString(clave, valor).commit()) {
            throw IOException("No se pudo persistir la caché cifrada de pólizas.")
        }
    }

    override fun leer(clave: String): String? = preferencias.getString(clave, null)

    override fun eliminar(clave: String) {
        preferencias.edit().remove(clave).commit()
    }

    override fun eliminarTodo() {
        preferencias.edit().clear().commit()
    }
}

internal data class ContenidoCifrado(
    val iv: String,
    val datos: String
)

private class CifradorCachePolizas(
    private val proveedorLlave: ProveedorLlaveCache
) {
    fun cifrar(texto: String, aad: ByteArray): ContenidoCifrado {
        val cipher = Cipher.getInstance(TRANSFORMACION)
        cipher.init(Cipher.ENCRYPT_MODE, proveedorLlave.obtener())
        cipher.updateAAD(aad)
        return ContenidoCifrado(
            iv = cipher.iv.aHex(),
            datos = cipher.doFinal(texto.toByteArray(Charsets.UTF_8)).aHex()
        )
    }

    fun descifrar(contenido: ContenidoCifrado, aad: ByteArray): String {
        val cipher = Cipher.getInstance(TRANSFORMACION)
        cipher.init(
            Cipher.DECRYPT_MODE,
            proveedorLlave.obtener(),
            GCMParameterSpec(BITS_ETIQUETA, contenido.iv.deHex())
        )
        cipher.updateAAD(aad)
        return String(cipher.doFinal(contenido.datos.deHex()), Charsets.UTF_8)
    }

    fun eliminarLlave() = proveedorLlave.eliminar()

    private companion object {
        const val TRANSFORMACION = "AES/GCM/NoPadding"
        const val BITS_ETIQUETA = 128
    }
}

private interface ProveedorLlaveCache {
    fun obtener(): SecretKey
    fun eliminar()
}

private class ProveedorLlaveFija(
    private val llave: SecretKey
) : ProveedorLlaveCache {
    override fun obtener(): SecretKey = llave
    override fun eliminar() = Unit
}

private class ProveedorLlaveKeystore : ProveedorLlaveCache {
    private val keyStore = KeyStore.getInstance(PROVEEDOR).apply { load(null) }

    override fun obtener(): SecretKey = llaveExistente() ?: crearLlave()

    override fun eliminar() {
        if (keyStore.containsAlias(ALIAS)) keyStore.deleteEntry(ALIAS)
    }

    private fun llaveExistente(): SecretKey? =
        (keyStore.getEntry(ALIAS, null) as? KeyStore.SecretKeyEntry)?.secretKey

    private fun crearLlave(): SecretKey {
        val constructor = KeyGenParameterSpec.Builder(
            ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .setRandomizedEncryptionRequired(true)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            constructor.setUnlockedDeviceRequired(true)
        }

        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, PROVEEDOR)
            .apply { init(constructor.build()) }
            .generateKey()
    }

    private companion object {
        const val PROVEEDOR = "AndroidKeyStore"
        const val ALIAS = "solventa_cache_polizas"
    }
}

private fun ByteArray.aHex(): String = joinToString("") { byte -> "%02x".format(byte) }

private fun String.deHex(): ByteArray {
    if (length % 2 != 0) throw GeneralSecurityException("Contenido cifrado inválido.")
    return chunked(2).map { parte ->
        parte.toIntOrNull(16)?.toByte()
            ?: throw GeneralSecurityException("Contenido cifrado inválido.")
    }.toByteArray()
}
