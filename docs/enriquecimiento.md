# Enriquecimiento del perfil con Open Finance y Open Data (HU10, BPM-56)

## Qué hace

Cuando el cliente tiene un consentimiento vigente, consulta en paralelo las fuentes externas autorizadas, traduce cada respuesta al modelo interno, las consolida en `SenalesPerfilamiento` y entrega ese modelo al perfil de riesgo (HU11). El asesor no digita datos financieros.

## Flujo

1. `POST /api/v1/consentimientos` registra el consentimiento (provisional, ver pendientes).
2. `POST /api/v1/enriquecimientos` con `cliente_id` y `cotizacion_id`:
   - verifica el consentimiento vigente; sin él no consulta ninguna fuente;
   - consulta Open Finance y Open Data en paralelo, cada una con tiempo límite;
   - consolida las señales y genera el perfil de riesgo;
   - devuelve las señales, la traza de cada fuente, el `perfil_id` y el dictamen.
3. `GET /api/v1/enriquecimientos/{cliente_id}` devuelve las señales consolidadas y su trazabilidad.

| Endpoint | Roles |
|---|---|
| `POST /api/v1/consentimientos` | Cliente, Asesor de Ventas, servicio interno |
| `POST /api/v1/enriquecimientos` | Asesor de Ventas, servicio interno |
| `GET /api/v1/enriquecimientos/{cliente_id}` | Analista de Riesgos, servicio interno |

| Respuesta | Cuándo |
|---|---|
| 201 | Señales consolidadas y perfil generado |
| 409 | El cliente no tiene consentimiento vigente |
| 503 | Una fuente falló y no hay un dato vigente en caché |

## Adaptadores y traducción

Cada proveedor tiene un adaptador que cumple el puerto `FuenteExterna`. El contrato externo no sale del adaptador.

| Fuente | Dato del proveedor | Señal interna |
|---|---|---|
| Open Finance | `payment_history.on_time_payments / total_payments` | `comportamiento_pago` |
| Open Finance | `monthly_debt_payments / monthly_income`, acotado a 1 | `nivel_endeudamiento` |
| Open Data | promedio de antigüedad laboral y de residencia, sobre 60 meses, acotado a 1 | `estabilidad` |
| Open Data | `zona_inmueble.indice_riesgo`: menos de 34 BAJO, menos de 67 MEDIO, resto ALTO | `riesgo_zona` |

Los contratos externos y estas fórmulas son los que definió el equipo de desarrollo para los simuladores; deben ajustarse cuando se conozca el contrato real de cada proveedor.

**Sumar una fuente (EC14):** escribir una clase con `tipo`, `proveedor` y `async consultar(cliente_id)` que devuelva `SenalesOpenFinance` o `SenalesOpenData`, y registrarla en `configuracion.py`. El servicio de enriquecimiento, la API y la HU11 no cambian.

## Caída de un proveedor (EC12)

- Cada respuesta correcta se guarda en caché por cliente y por fuente durante 24 horas.
- Si una fuente falla o supera el tiempo límite, se usa su último dato vigente. La otra fuente se sigue consultando en vivo.
- El uso de caché queda en tres sitios: `origen: CACHE` en las señales y en el perfil, la traza de la fuente con el motivo, y una línea `uso_de_cache` en el log `solventa.auditoria.enriquecimiento`.
- Sin dato vigente en caché no se inventa nada: la solicitud responde 503.

Cuenta como falla: tiempo agotado, error de conexión, código HTTP distinto de 200, respuesta que no es JSON y respuesta con campos faltantes o fuera de rango.

## Seguridad de la transmisión (EC07)

El cliente HTTP compartido:
- rechaza URL que no sean `https://`, salvo permiso explícito para desarrollo local;
- exige TLS 1.2 o superior y valida el certificado del proveedor;
- envía un token de portador en cada solicitud y no arranca sin token.

## Configuración

| Variable | Uso | Por defecto |
|---|---|---|
| `OPEN_FINANCE_URL`, `OPEN_FINANCE_TOKEN` | Agregador de Open Finance | Simulador en proceso |
| `OPEN_DATA_URL`, `OPEN_DATA_TOKEN` | Fuente de Open Data | Simulador en proceso |
| `FUENTES_TIEMPO_LIMITE_SEGUNDOS` | Tiempo límite por fuente | 0.25 |
| `FUENTES_PERMITIR_HTTP` | `true` permite `http://` | No permitido |

Sin URL configurada se usan simuladores en proceso, deterministas por cliente, para correr el backend en local.

## Pendientes conocidos

- **Consentimiento provisional:** el registro y la consulta de consentimientos pertenecen al servicio de Identidad, KYC y Consentimiento. Aquí están en memoria detrás del puerto `RepositorioConsentimientos`.
- **Proceso de cotización autorizado:** solo se exige que la solicitud traiga `cotizacion_id`. No se valida contra el servicio de cotización, que es de la HU03 (Sprint 2).
- **Autenticación provisional:** el rol se lee de la cabecera `X-Rol` hasta que la HU19 entregue el token.
- **EC07 parcial:** la autenticación es por token de portador. No hay mTLS ni tokens firmados por solicitud, y no se han hecho pruebas de intrusión.
- **EC12 parcial:** el comportamiento está probado, pero la disponibilidad del 99,9 % no se ha medido en un ambiente desplegado.
- **Caché en memoria:** falta el adaptador de ElastiCache Redis; hoy la caché no se comparte entre instancias ni sobrevive a un reinicio.
- **Proveedores reales:** los adaptadores HTTP están probados contra respuestas simuladas, no contra un proveedor real.
