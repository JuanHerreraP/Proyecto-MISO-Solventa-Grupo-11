# Modificación de coberturas y endosos de la póliza (HU16)

## Qué hace

El cliente asegurado, o el asesor de ventas que asistió la venta, modifica una póliza vigente desde el portal web:

- **Beneficiarios** (solo seguros de vida, incluido vida hipotecario): agregar, editar o retirar beneficiarios. Si hay beneficiarios, sus porcentajes deben sumar exactamente 100 %. Sin beneficiarios, la indemnización va a los herederos legales.
- **Coberturas opcionales**: incluir, aumentar, reducir o excluir amparos adicionales del ramo.
- **Ajuste de prima**: el backend calcula al instante el ajuste pro-rata por los días que le quedan a la póliza. Un ajuste positivo es un cobro; uno negativo, una devolución de prima no devengada.
- **Endoso**: al confirmar, se emite un PDF de endoso que queda disponible para descarga de inmediato. El PDF de la póliza (HU12) no se modifica.

## Flujo en el portal

1. En **Mis pólizas**, en el detalle de una póliza vigente, el cliente abre **Modificar coberturas y beneficiarios** (`/polizas/{poliza_id}/modificar`).
2. Ajusta coberturas y beneficiarios y pulsa **Calcular ajuste de prima** (simulación; no guarda nada).
3. Revisa los cambios, el ajuste y la nueva prima, acepta y pulsa **Confirmar y emitir endoso**.
4. Descarga el PDF del endoso. El historial de endosos de la póliza queda en la misma pantalla.

Cualquier edición después de calcular obliga a recalcular. El servidor siempre vuelve a calcular al confirmar; no confía en el valor que vio el portal.

## Endpoints

Todos exigen sesión de un usuario `CLIENTE` (sus pólizas) o `ASESOR_VENTAS` (pólizas de ventas que asistió).

| Método y ruta | Devuelve |
|---|---|
| `GET /api/v1/polizas/{poliza_id}/endosos/opciones` | Estado de la póliza, coberturas opcionales disponibles con sus límites, coberturas y beneficiarios actuales |
| `POST /api/v1/polizas/{poliza_id}/endosos/simulacion` | La propuesta: cambios, fecha de efecto, días, ajuste, concepto y nueva prima |
| `POST /api/v1/polizas/{poliza_id}/endosos` | Confirma y emite el endoso (201; 200 si se repite con la misma `Idempotency-Key`) |
| `GET /api/v1/polizas/{poliza_id}/endosos` | Historial de endosos, del más antiguo al más reciente |
| `GET /api/v1/polizas/{poliza_id}/endosos/{endoso_id}/documento` | PDF del endoso, con su huella en `X-Huella-Documento` |

El cuerpo de la simulación y de la confirmación es el **estado deseado**:

```json
{
  "beneficiarios": [
    {"nombre_completo": "Mateo Gómez", "tipo_documento": "CC", "numero_documento": "1098765432",
     "parentesco": "Hijo", "porcentaje": "60"},
    {"nombre_completo": "Sofía Gómez", "tipo_documento": "TI", "numero_documento": "1098765433",
     "parentesco": "Hija", "porcentaje": "40"}
  ],
  "coberturas_opcionales": [
    {"codigo": "INCAPACIDAD_TOTAL_PERMANENTE", "suma_asegurada": "50000000"}
  ],
  "acepta_condiciones": true
}
```

Un campo ausente no cambia; una lista vacía quita todo. `acepta_condiciones` solo se exige al confirmar.

### Códigos de respuesta

| Código | Cuándo |
|---|---|
| 401 | Sin sesión |
| 403 | El actor no es cliente ni asesor, o `ACCESO_DENEGADO`: el asesor no participó en la venta |
| 404 | `POLIZA_NO_ENCONTRADA` (no existe o es de otro cliente), `ENDOSO_NO_ENCONTRADO` |
| 409 | `POLIZA_NO_MODIFICABLE` (vencida o cancelada), `MODIFICACION_CONCURRENTE`, `CLAVE_IDEMPOTENCIA_REUTILIZADA`, `DOCUMENTO_ALTERADO` |
| 422 | `SIN_CAMBIOS`, `PORCENTAJES_NO_SUMAN_100`, `BENEFICIARIO_DUPLICADO`, `BENEFICIARIO_ES_TITULAR`, `DEMASIADOS_BENEFICIARIOS`, `BENEFICIARIOS_NO_APLICAN`, `COBERTURA_NO_DISPONIBLE`, `COBERTURA_DUPLICADA`, `SUMA_FUERA_DE_RANGO`, `CONFIRMACION_REQUERIDA` |
| 503 | `ALMACEN_NO_DISPONIBLE` |

Los errores de negocio llegan en `detail` con `codigo`, `mensaje` y, cuando aplica, `campo`.

## Cálculo del ajuste

- Tarifa de una cobertura opcional por toda la vigencia: `suma asegurada × tasa mensual × días de vigencia / 30`.
- Ajuste: `(tarifa de las opcionales nuevas − tarifa de las anteriores) × días restantes / días de vigencia`, redondeado a centavos (mitad hacia arriba).
- Los días cuentan inclusive: rige desde hoy (hora Colombia) o desde el inicio de la póliza si aún no empieza, hasta su último día.
- La nueva prima total de la póliza es la prima anterior más el ajuste.

Ejemplo: vida con vigencia de 365 días, se incluye incapacidad total y permanente por $50.000.000 (tasa 0,012 %) cuando faltan 183 días. Tarifa anual $73.000; ajuste $36.600.

Catálogo (`app/polizas/dominio/endosos.py`, versión de tarifas `2026.11.1`):

| Ramo | Cobertura | Tasa mensual | Suma |
|---|---|---|---|
| Vida | Incapacidad total y permanente | 0,012 % | $1M a $500M, sin superar la principal |
| Vida | Enfermedades graves | 0,020 % | $1M a $200M, sin superar la principal |
| Vida | Auxilio funerario | 0,030 % | $1M a $10M |
| Viaje | Cancelación del viaje | 0,40 % | $500 mil a $20M |
| Viaje | Pérdida de equipaje | 0,30 % | $500 mil a $10M |
| Dispositivos | Accesorios | 0,60 % | $100 mil a $3M |
| Dispositivos | Garantía extendida | 0,40 % | $100 mil a $20M, sin superar la principal |
| Paramétrico | — | — | No tiene coberturas opcionales |

## Trazabilidad e integridad (EC10)

- Un endoso es inmutable. Cada cambio posterior genera un endoso nuevo con el número siguiente.
- Cada endoso registra quién lo pidió (`solicitado_por`, `rol_solicitante`), la IP y el navegador, la huella SHA-256 de la solicitud y la del PDF, y el linaje de cada cambio (`antes` y `despues`). HU25 puede leer este historial.
- Endoso y póliza actualizada se guardan en una sola transacción. La restricción única `(poliza_id, numero_endoso)` impide que dos confirmaciones simultáneas generen el mismo número: la segunda recibe `MODIFICACION_CONCURRENTE`.
- `Idempotency-Key`: repetir la confirmación con la misma clave y la misma solicitud devuelve el mismo endoso; con otra solicitud se rechaza.
- La descarga verifica la huella del PDF antes de entregarlo.

## Persistencia

- Tabla nueva `endosos` (la crea `create_all`).
- Columnas nuevas y nulas en `polizas`: `coberturas_opcionales` y `beneficiarios` (JSON). `preparar_esquema_registro` las agrega en bases existentes; las pólizas anteriores se leen con listas vacías.
- El PDF se guarda en el mismo almacén de documentos de HU12 (S3 con respaldo en disco), bajo `endosos/{poliza_id}/`.

## Fuera del alcance

- **Cobro o devolución del ajuste**: el endoso calcula y registra el ajuste y la nueva prima, pero no ejecuta el cobro ni el reembolso en la pasarela. Eso queda para el flujo de pagos (HU21) y de cancelación con devolución (HU18).
- **Factor de riesgo (HU11)**: la tarifa de las opcionales no aplica el factor del perfil de riesgo, porque la póliza no guarda el factor con que se cotizó. Si el equipo lo quiere, hay que guardarlo al emitir.
- **App Android**: esta historia cubre el portal web. La consulta móvil del historial está en HU09.
