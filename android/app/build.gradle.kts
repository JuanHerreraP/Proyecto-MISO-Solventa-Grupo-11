import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
    // HU05: lee google-services.json para conectar la app con el proyecto de Firebase.
    alias(libs.plugins.google.services)
    jacoco
}

android {
    namespace = "com.example.solventa"
    compileSdk {
        version = release(37)
    }

    defaultConfig {
        applicationId = "com.example.solventa"
        minSdk = 24
        targetSdk = 37
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        // Backend local visto desde el emulador. Para otro ambiente:
        // ./gradlew assembleDebug -Psolventa.apiBaseUrl=https://api.ejemplo.com/
        val apiBaseUrl = providers.gradleProperty("solventa.apiBaseUrl")
            .getOrElse("http://10.0.2.2:8000/")
        buildConfigField("String", "API_BASE_URL", "\"$apiBaseUrl\"")

        // HU06: clave de Google Maps. NUNCA se versiona una clave real.
        // Orden de lectura:
        //   1) local.properties -> solventa.mapsApiKey   (archivo NO versionado; recomendado en local)
        //   2) propiedad de Gradle -Psolventa.mapsApiKey  (línea de comandos / CI)
        // Sin clave queda vacía: la app compila y el mapa simplemente no carga mosaicos.
        val localProperties = Properties().apply {
            val archivo = rootProject.file("local.properties")
            if (archivo.exists()) archivo.inputStream().use { entrada -> load(entrada) }
        }
        val mapsApiKey = localProperties.getProperty("solventa.mapsApiKey")
            ?: providers.gradleProperty("solventa.mapsApiKey").getOrElse("")
        manifestPlaceholders["mapsApiKey"] = mapsApiKey
    }

    buildTypes {
        debug {
            // Reporte de coverage de las pruebas unitarias:
            // ./gradlew createDebugUnitTestCoverageReport
            enableUnitTestCoverage = true
        }
        release {
            optimization {
                enable = true
                packageScope = setOf("androidx.**", "kotlin.**", "kotlinx.**")
            }
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    testOptions {
        unitTests {
            // Robolectric necesita los recursos para renderizar las pantallas Compose.
            isIncludeAndroidResources = true
            isReturnDefaultValues = true
        }
    }
}

// Las pantallas se prueban con Robolectric, que carga las clases con su propio classloader.
// Sin esto JaCoCo las ignora y aparecen con 0 % de coverage.
tasks.withType<Test>().configureEach {
    extensions.configure<JacocoTaskExtension> {
        isIncludeNoLocationClasses = true
        excludes = listOf("jdk.internal.*")
    }
}

dependencies {
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation("androidx.compose.ui:ui-text-google-fonts:1.6.0")
    implementation("androidx.navigation:navigation-compose:2.8.0")
    implementation("androidx.compose.material:material-icons-extended")
    // HU02: biometría, sesión y red
    implementation(libs.androidx.biometric)
    implementation(libs.androidx.fragment.ktx)
    implementation(libs.androidx.activity.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.ktx)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.retrofit)
    implementation(libs.retrofit.converter.gson)
    implementation(libs.gson)
    implementation(libs.okhttp)
    // HU05: notificaciones push con Firebase Cloud Messaging
    implementation(platform(libs.firebase.bom))
    implementation(libs.firebase.messaging)
    // HU07: código QR del certificado, generado en el dispositivo
    implementation(libs.zxing.core)
    // HU06: mapa de prestadores cercanos y ubicación actual
    implementation(libs.maps.compose)
    implementation(libs.play.services.maps)
    implementation(libs.play.services.location)
    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.okhttp.mockwebserver)
    testImplementation(libs.robolectric)
    testImplementation(platform(libs.androidx.compose.bom))
    testImplementation(libs.androidx.compose.ui.test.junit4)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(libs.androidx.junit)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
    debugImplementation(libs.androidx.compose.ui.tooling)
}
