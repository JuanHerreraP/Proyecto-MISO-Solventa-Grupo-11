package com.example.solventa

import android.os.Bundle
import android.view.WindowManager
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.ui.Modifier
import androidx.fragment.app.FragmentActivity
import com.example.solventa.biometric.AutenticadorBiometrico
import com.example.solventa.biometric.DisponibilidadBiometrica
import com.example.solventa.data.remote.ApiClient
import com.example.solventa.data.remote.RemoteAuthGateway
import com.example.solventa.data.session.KeystoreBovedaSesion
import com.example.solventa.domain.auth.AuthCoordinator
import com.example.solventa.domain.auth.Reloj
import com.example.solventa.ui.auth.AuthViewModel
import com.example.solventa.ui.navigation.NavGraph
import com.example.solventa.ui.theme.SolventaTheme

/** FragmentActivity porque BiometricPrompt la necesita para mostrar su diálogo. */
class MainActivity : FragmentActivity() {

    private val autenticador by lazy { AutenticadorBiometrico(this) }

    private val viewModel: AuthViewModel by viewModels {
        AuthViewModel.Fabrica {
            AuthCoordinator(
                gateway = RemoteAuthGateway(ApiClient.crearAuthApi()),
                boveda = KeystoreBovedaSesion(applicationContext),
                reloj = Reloj { System.currentTimeMillis() },
                biometriaDisponible = {
                    autenticador.disponibilidad() == DisponibilidadBiometrica.DISPONIBLE
                }
            )
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Evita capturas de pantalla y que la vista previa de recientes muestre datos del cliente.
        window.setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE)
        enableEdgeToEdge()
        setContent {
            SolventaTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
                    NavGraph(
                        viewModel = viewModel,
                        autenticador = autenticador,
                        modifier = Modifier.padding(innerPadding)
                    )
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        // Al volver a la app se revisa si el access token venció mientras estaba en segundo plano.
        viewModel.verificarExpiracion()
    }
}
