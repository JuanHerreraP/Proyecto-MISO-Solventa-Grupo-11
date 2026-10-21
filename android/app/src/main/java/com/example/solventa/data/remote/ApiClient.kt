package com.example.solventa.data.remote

import com.example.solventa.BuildConfig
import java.util.concurrent.TimeUnit
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object ApiClient {
    /**
     * La URL base sale de `BuildConfig.API_BASE_URL`. Por defecto apunta al backend local
     * desde el emulador (10.0.2.2 es el localhost del computador).
     */
    fun crearAuthApi(urlBase: String = BuildConfig.API_BASE_URL): AuthApi =
        retrofit(urlBase).create(AuthApi::class.java)

    /** Billetera de pólizas (HU07). */
    fun crearPolizasApi(urlBase: String = BuildConfig.API_BASE_URL): PolizasApi =
        retrofit(urlBase).create(PolizasApi::class.java)

    private val cliente: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(15, TimeUnit.SECONDS)
            .build()
    }

    private fun retrofit(urlBase: String): Retrofit = Retrofit.Builder()
        .baseUrl(urlBase)
        .client(cliente)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
}
