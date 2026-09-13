# Experimento 3 — Facilidad de modificación mediante Puertos y Adaptadores (EC06)

## Qué valida

**Hipótesis de diseño:** si la integración de KYC se implementa mediante el patrón Puertos y Adaptadores, manteniendo una interfaz interna estable (`IdentityVerificationProvider`) entre el servicio de Identidad y los proveedores externos, entonces es posible sustituir el proveedor KYC sin modificar el servicio de Identidad ni los demás componentes consumidores.

**Punto de sensibilidad:** el contrato del puerto `IdentityVerificationProvider` entre el servicio de Identidad y la implementación concreta del proveedor KYC.

## Estructura

```
app/
  domain/
    models.py      # VerificationRequest / VerificationResult / VerificationStatus (modelo agnóstico de proveedor)
    ports.py        # IdentityVerificationProvider (el puerto)
  adapters/
    kyc_provider_a.py  # Adaptador + cliente simulado del Proveedor A (contrato REST plano, en inglés)
    kyc_provider_b.py  # Adaptador + cliente simulado del Proveedor B (contrato anidado, en español, confianza invertida)
  config.py          # Lee KYC_PROVIDER (env var) — único mecanismo de configuración
  main.py             # Servicio de Identidad (consumidor): endpoint /identidad/verificaciones
tests/
  test_contract_regression.py   # Suite de regresión: MISMAS pruebas corridas contra Proveedor A y Proveedor B
  test_adapter_provider_a.py    # Unitarias del adaptador A (traducción de contrato)
  test_adapter_provider_b.py    # Unitarias del adaptador B (traducción de contrato)
```

El servicio (`app/main.py`) es el "consumidor" bajo prueba: en ningún punto de ese archivo se referencia `KYCProviderAAdapter` ni `KYCProviderBAdapter` fuera de la función de ensamblaje `get_identity_verification_provider`. Esa función lee la variable de entorno `KYC_PROVIDER` y decide qué adaptador inyectar — es el único lugar del servicio que conoce que existen dos proveedores.

Los dos proveedores simulados tienen contratos **deliberadamente distintos** para que la sustitución sea una prueba real y no un caso trivial:

| | Proveedor A | Proveedor B |
|---|---|---|
| Forma de la solicitud | Campos planos, en inglés | Objeto anidado (`solicitante`), en español |
| Formato de fecha | `YYYY-MM-DD` | `DD/MM/YYYY` |
| Vocabulario de estado | `APPROVED` / `REJECTED` / `PENDING` | `OK` / `RECHAZADO` / `EN_REVISION` |
| Escala del puntaje | Entero 0-100 (a mayor score, mayor riesgo) | Flotante 0.0-1.0 (a mayor score, **menor** riesgo — es confianza, no riesgo) |

## Cómo correrlo

**Linux / macOS (bash):**

```bash
cd experimentos/experimento-3-puertos-adaptadores-kyc
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Suite completa (parametrizada internamente sobre A y B)
pytest -v

# Levantar el servicio con un proveedor u otro (para probar manualmente / grabar evidencia en video)
KYC_PROVIDER=A uvicorn app.main:app --port 8001
KYC_PROVIDER=B uvicorn app.main:app --port 8002
```

**Windows (PowerShell):**

```powershell
cd experimentos\experimento-3-puertos-adaptadores-kyc
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

pytest -v

$env:KYC_PROVIDER = "A"
uvicorn app.main:app --port 8001
```

## Evidencia de ejecución (2026-09-10)

**Regresión automatizada — 3 corridas independientes, mismo resultado:**

| Entorno | Resultado |
|---|---|
| Sandbox cloud (Linux, Python 3.11) | 16/16 pasan con `KYC_PROVIDER=A` y 16/16 con `KYC_PROVIDER=B` |
| Puente al equipo del integrante (Linux VM, Python 3.10) | 16/16 pasan con `KYC_PROVIDER=A` y 16/16 con `KYC_PROVIDER=B` |
| PowerShell del integrante (Windows, Python 3.14, venv real del proyecto) | `pytest -v` corrido por el integrante — 16/16 pasan |

```
======================== 16 passed, 1 warning in 0.07s =========================   (KYC_PROVIDER=A)
======================== 16 passed, 1 warning in 0.06s =========================   (KYC_PROVIDER=B)
```

**Prueba manual del servicio real, en tres entornos distintos, mismo resultado byte a byte:**

```
--- Proveedor A ---
POST /identidad/verificaciones -> {
    "verification_id": "A-1000000034-4489",
    "status": "REJECTED",
    "risk_score": 0.89,
    "checked_at": "2026-09-10T00:17:51.005768"
}
GET /salud -> {"status":"ok","proveedor_kyc_activo":"A"}

--- Proveedor B ---
POST /identidad/verificaciones -> {
    "verification_id": "B-1000000034-4489",
    "status": "REJECTED",
    "risk_score": 0.81,
    "checked_at": "2026-09-10T00:17:52.684556"
}
GET /salud -> {"status":"ok","proveedor_kyc_activo":"B"}
```

El integrante repitió esta misma llamada de forma independiente en su propia máquina Windows con `Invoke-RestMethod` (puertos 8001 y 8002) y obtuvo exactamente los mismos valores: `A-1000000034-4489` / `REJECTED` / `0.89` para el Proveedor A, y `B-1000000034-4489` / `REJECTED` / `0.81` para el Proveedor B. Esto confirma que el experimento es determinístico y reproducible independientemente del sistema operativo o de quién lo ejecute — no es un resultado que solo se dio una vez en un ambiente controlado.

El contrato de respuesta hacia el consumidor (forma del JSON, nombres de campos, vocabulario de estado, escala 0.0-1.0 del riesgo) es idéntico sin importar el proveedor activo. La diferencia de `risk_score` (0.89 vs. 0.81) es esperable y correcta: cada proveedor simulado calcula el riesgo con su propia lógica interna; lo que el experimento valida no es que ambos den el mismo número, sino que **ninguna de esas diferencias se filtra fuera del adaptador**.

## CI — regresión automática

`.github/workflows/experimento-3-kyc-regression.yml` ejecuta esta misma suite en GitHub Actions dos veces en paralelo (matriz `KYC_PROVIDER: [A, B]`), en cada push/PR que toque esta carpeta, y publica el resultado de cada corrida como artefacto (`resultados-A.xml` / `resultados-B.xml`) — esta es la evidencia a enlazar en el video de la Entrega 6.

## Interpretación de resultados

Tabla de interpretación definida desde el diseño del experimento en Semana 4 (ver `claude/SEmana 4` / `claude/Semana 5` en el proyecto), con el resultado real obtenido resaltado:

| Resultado posible | Interpretación | ¿Ocurrió en esta ejecución? |
|---|---|---|
| El proveedor se sustituye modificando únicamente el adaptador y existen cero cambios en los consumidores | **La evidencia obtenida soporta la hipótesis de diseño y el criterio evaluado de EC06.** | ✅ **Sí — este es el resultado obtenido.** |
| Es necesario modificar el servicio de Identidad u otro consumidor | La hipótesis queda refutada porque el cambio del proveedor se propagó fuera del adaptador. | No. `app/main.py` no se tocó entre la corrida con Proveedor A y con Proveedor B. |
| Es necesario modificar el puerto `IdentityVerificationProvider` | El contrato interno presenta acoplamiento con las particularidades del proveedor y debe revisarse antes de considerar validada la hipótesis. | No. `app/domain/ports.py` no cambió; el puerto siguió siendo `verify(request) -> result` en ambos casos. |
| El cambio queda aislado en el adaptador, pero aparecen fallos en la regresión | La localización estructural del cambio funciona, pero la sustitución no mantiene completamente el comportamiento esperado. Se requiere analizar los contratos y transformaciones involucrados. | No. Las 16 pruebas de la suite de regresión (contrato + validación de entrada + salud) pasaron igual con ambos proveedores, en tres entornos distintos. |

### Conclusión

La evidencia recolectada — 16/16 pruebas automatizadas pasando igual con ambos proveedores en tres entornos independientes (sandbox cloud, puente remoto, y la máquina Windows del integrante), más la verificación manual del servicio real con resultados idénticos y reproducibles — **soporta la hipótesis de diseño**. El patrón Puertos y Adaptadores, implementado mediante el puerto `IdentityVerificationProvider` y adaptadores concretos por proveedor, permite sustituir el proveedor KYC sin propagar el cambio al servicio de Identidad ni a los demás componentes consumidores. Esto valida el criterio de calidad **EC06 — Facilidad de modificación** para el punto de sensibilidad evaluado (cambio de proveedor KYC).

No se presentaron indicios de acoplamiento entre el puerto y las particularidades de ningún proveedor, ni fue necesario ajustar la interfaz `IdentityVerificationProvider` durante la implementación de ninguno de los dos adaptadores — un indicador adicional (no parte de la tabla original, pero relevante) de que el diseño de la interfaz fue lo suficientemente pequeño y orientado al negocio como para no filtrar detalles de un proveedor específico.

**Decisiones de diseño confirmadas por esta evidencia:**
- Mantener `IdentityVerificationProvider` como la única vía de acceso del servicio de Identidad a la verificación KYC (sin llamadas directas a proveedores desde otros puntos del código).
- Mantener la traducción de contrato (nombres de campo, formato de fecha, vocabulario de estado, normalización de score) encapsulada dentro de cada adaptador, y no en el servicio consumidor.

**Decisiones que no fue necesario corregir o revisar:** ninguna — no se identificó ningún punto donde el diseño actual del puerto o del servicio de Identidad necesitara ajustarse a partir de este experimento.

