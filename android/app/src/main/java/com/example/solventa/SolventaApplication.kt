package com.example.solventa

import android.app.Application
import com.example.solventa.data.push.CanalNotificaciones

class SolventaApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        // El canal debe existir antes de que llegue el primer push, aunque la app esté cerrada.
        CanalNotificaciones.crear(this)
    }
}
