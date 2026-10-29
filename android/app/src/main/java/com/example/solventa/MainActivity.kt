package com.example.solventa

import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import com.example.solventa.biometric.AutenticadorBiometrico
import com.example.solventa.biometric.DisponibilidadBiometrica
import com.example.solventa.data.remote.ApiClient
import com.example.solventa.data.remote.RemoteAuthGateway
import com.example.solventa.data.remote.RemoteCotizacionesGateway
import com.example.solventa.data.remote.RemotePagosGateway
import com.example.solventa.data.remote.RemotePolizasGateway
import com.example.solventa.data.session.KeystoreBovedaSesion
import com.example.solventa.domain.auth.AuthCoordinator
import com.example.solventa.domain.auth.Reloj
import com.example.solventa.domain.cotizaciones.CotizacionesCoordinator
import com.example.solventa.domain.pagos.PagosCoordinator
import com.example.solventa.domain.polizas.BilleteraCoordinator
import com.example.solventa.ui.auth.AuthViewModel
import com.example.solventa.ui.billetera.BilleteraViewModel
import com.example.solventa.ui.cotizaciones.CotizacionesViewModel
import com.example.solventa.ui.pagos.PagosViewModel
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

    /** La billetera usa la misma sesión que el ingreso para pedir sus datos al backend. */
    private val billetera: BilleteraViewModel by viewModels {
        BilleteraViewModel.Fabrica {
            BilleteraCoordinator(
                gateway = RemotePolizasGateway(ApiClient.crearPolizasApi()),
                sesion = viewModel.sesion
            )
        }
    }

    private val cotizaciones: CotizacionesViewModel by viewModels {
        CotizacionesViewModel.Fabrica {
            CotizacionesCoordinator(
                gateway = RemoteCotizacionesGateway(ApiClient.crearCotizacionesApi()),
                sesion = viewModel.sesion
            )
        }
    }

    private val pagos: PagosViewModel by viewModels {
        PagosViewModel.Fabrica {
            PagosCoordinator(
                gateway = RemotePagosGateway(ApiClient.crearPagosApi()),
                sesion = viewModel.sesion
            )
        }
    }

    private val solicitarRedLocal =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        pedirPermisoRedLocalSiAplica()
        // Evita capturas de pantalla y que la vista previa de recientes muestre datos del cliente.
        window.setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE)
        enableEdgeToEdge()
        setContent {
            SolventaTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
                    NavGraph(
                        viewModel = viewModel,
                        autenticador = autenticador,
                        modifier = Modifier.padding(innerPadding),
                        billetera = billetera,
                        cotizaciones = cotizaciones,
                        pagos = pagos
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

    /**
     * Desde Android 17 (API 37) las conexiones a IPs de la red local (10.0.2.2, 192.168.x.x...)
     * fallan sin ACCESS_LOCAL_NETWORK. Solo se pide cuando el backend configurado es local.
     */
    private fun pedirPermisoRedLocalSiAplica() {
        if (Build.VERSION.SDK_INT < 37 || !esBackendLocal(BuildConfig.API_BASE_URL)) return
        val permiso = "android.permission.ACCESS_LOCAL_NETWORK"
        if (ContextCompat.checkSelfPermission(this, permiso) != PackageManager.PERMISSION_GRANTED) {
            solicitarRedLocal.launch(permiso)
        }
    }

    private fun esBackendLocal(url: String): Boolean {
        val host = Uri.parse(url).host ?: return false
        return host == "localhost" ||
            host.startsWith("10.") ||
            host.startsWith("192.168.") ||
            host.startsWith("127.") ||
            Regex("^172\\.(1[6-9]|2\\d|3[01])\\.").containsMatchIn(host)
    }
}
