package com.example.solventa

import android.app.Application
import com.example.solventa.data.push.CanalNotificaciones
import com.example.solventa.i18n.Idioma

class SolventaApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        // Idioma guardado por el usuario (español por defecto); antes de pintar cualquier texto.
        Idioma.iniciar(this)
        // El canal debe existir antes de que llegue el primer push, aunque la app esté cerrada.
        CanalNotificaciones.crear(this)
    }
}
