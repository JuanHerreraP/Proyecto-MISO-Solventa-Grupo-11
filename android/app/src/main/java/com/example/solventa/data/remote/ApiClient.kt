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
    fun crearAuthApi(urlBase: String = BuildConfig.API_BASE_URL): AuthApi {
        val cliente = OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(15, TimeUnit.SECONDS)
            .build()

        return Retrofit.Builder()
            .baseUrl(urlBase)
            .client(cliente)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(AuthApi::class.java)
    }
}
