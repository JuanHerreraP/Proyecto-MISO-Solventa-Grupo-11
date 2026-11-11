# Historial detallado de movimientos de una póliza (HU25 / CPM-72)

Como **Cliente Asegurado** (o un rol interno de solo lectura), consultar la bitácora histórica
de transacciones y cambios contractuales de una póliza para tener transparencia sobre los
cobros y modificaciones realizadas a la protección contratada.

## Qué hace

HU25 es una **vista consolidada de solo lectura**. No crea movimientos ni tablas nuevas: lee
las fuentes de verdad que ya mantienen otros módulos, las normaliza a un modelo neutral
(`MovimientoPoliza`) y las entrega ordenadas del más reciente al más antiguo.

```
Póliza ──► Emisión (HU12)
       ├─► Pago inicial (HU13)
       ├─► Endosos (HU16)
       └─► Desembolsos (HU15)
                 │
                 ▼
        ServicioHistorialPoliza  (normaliza + ordena)
                 │
                 ▼
   GET /api/v1/polizas/{id}/historial
                 │
                 ▼
         Portal web · Historial de la póliza
```

## Fuentes integradas

| Fuente | HU | Relación con la póliza | Tipo de movimiento |
|---|---|---|---|
| Emisión | HU12 | `poliza.emitida_en` | `EMISION` (categoría `POLIZA`) |
| Pago inicial | HU13 | `poliza.cotizacion_id == pago.cotizacion_id` | `PAGO_PRIMA_INICIAL` (`FINANCIERO`) |
| Endosos | HU16 | `endoso.poliza_id` | `ENDOSO` (`CONTRACTUAL`) |
| Desembolsos | HU15 | `desembolso.poliza_id` | `DESEMBOLSO_INDEMNIZACION` (`FINANCIERO`) |
| Cancelación | — | `poliza.cancelada_en` | `CANCELACION` (`CONTRACTUAL`) |

El pago se vincula por `cotizacion_id` (HU13 no guarda `poliza_id`), por lo que no fue necesario
modificar HU13. Los desembolsos en estado `FALLIDA` no se incluyen: no representan dinero
entregado al cliente.

## Endpoint

```
GET /api/v1/polizas/{poliza_id}/historial
```

- Respuesta `200`: `HistorialPoliza { poliza_id, numero_poliza, movimientos[] }`.
- Encabezado `Cache-Control: no-store` (información contractual y financiera sensible).
- Es estrictamente de lectura: no existen `POST`/`PUT`/`DELETE` de historial.

### Ejemplo de respuesta (abreviado)

```json
{
  "poliza_id": "POL-001",
  "numero_poliza": "SOLV-VIA-2026-00152",
  "movimientos": [
    {
      "movimiento_id": "END-001-002",
      "categoria": "CONTRACTUAL",
      "tipo": "ENDOSO",
      "fecha": "2026-11-04T15:40:00Z",
      "descripcion": "Endoso #2",
      "referencia": "END-001-002",
      "estado": "COMPLETADO",
      "monto": "25000.00",
      "moneda": "COP",
      "naturaleza_monto": "AJUSTE",
      "cambios": [
        {
          "tipo": "COBERTURA_INCLUIDA",
          "descripcion": "Se incluye Pérdida de equipaje.",
          "antes": null,
          "despues": { "codigo": "EQUIPAJE", "nombre": "Pérdida de equipaje", "suma_asegurada": "5000000.00" }
        }
      ],
      "consentimiento": {
        "explicito": true,
        "tipo": "CONFIRMACION_ENDOSO",
        "usuario_id": "USR-1",
        "rol": "CLIENTE",
        "fecha": "2026-11-04T15:40:00Z",
        "huella_solicitud": "..."
      }
    },
    {
      "movimiento_id": "PAY-001",
      "categoria": "FINANCIERO",
      "tipo": "PAGO_PRIMA_INICIAL",
      "fecha": "2026-10-20T13:45:00Z",
      "descripcion": "Pago de prima inicial",
      "referencia": "PAY-001",
      "referencia_externa": "PSP-88910",
      "estado": "APROBADO",
      "monto": "125000.00",
      "moneda": "COP",
      "naturaleza_monto": "COBRO",
      "cambios": [],
      "consentimiento": null
    },
    {
      "movimiento_id": "POL-001-EMISION",
      "categoria": "POLIZA",
      "tipo": "EMISION",
      "fecha": "2026-10-20T14:05:00Z",
      "descripcion": "Póliza emitida",
      "referencia": "SOLV-VIA-2026-00152",
      "estado": "COMPLETADO",
      "monto": null,
      "cambios": [],
      "consentimiento": null
    }
  ]
}
```

## Permisos

| Rol | Acceso |
|---|---|
| `CLIENTE` | Solo el historial de **sus propias** pólizas. El `cliente_id` sale de la sesión; el frontend nunca lo envía. Una póliza ajena responde `403`. |
| `SERVICIO_INTERNO`, `OPERACIONES_SINIESTROS` | Lectura del historial de cualquier póliza (apoyo de auditoría/cumplimiento). |
| Otros roles | `403`. |

El proyecto aún no define un rol `AUDITOR`/`ANALISTA_CUMPLIMIENTO` dedicado. Cuando exista,
basta añadirlo a `ROLES_LECTURA_INTERNA` en `app/api/historial_poliza.py`; no se inventó un
enum de roles nuevo para esta HU.

### Códigos HTTP

| Código | Situación |
|---|---|
| `200` | Historial consultado. |
| `401` | Sin token válido. |
| `403` | Póliza de otro cliente o rol sin permiso. |
| `404` | La póliza no existe. |

## Modelo de movimiento

- `categoria`: `FINANCIERO` \| `CONTRACTUAL` \| `POLIZA`.
- `tipo`: `EMISION`, `PAGO_PRIMA_INICIAL`, `ENDOSO`, `RENOVACION`, `CANCELACION`,
  `DESEMBOLSO_INDEMNIZACION`, `REEMBOLSO`.
- `naturaleza_monto`: `COBRO`, `REEMBOLSO`, `INDEMNIZACION`, `AJUSTE`. El `monto` siempre es
  **positivo**; el signo mostrado al cliente lo decide la UI según la naturaleza (un cobro se
  muestra con `-`, una indemnización con `+`).
- Movimientos financieros exponen `referencia` (id interno) y `referencia_externa` (id de la
  pasarela). Si no hay referencia de pasarela se devuelve `null` y la UI muestra
  "Sin referencia externa"; no se inventa una.
- Movimientos contractuales exponen `cambios[]` con el linaje `antes`/`despues` reutilizado de
  HU16, y `consentimiento` con la evidencia de aceptación explícita del endoso.

## Orden cronológico

El backend es la fuente de verdad del orden. Tras reunir todos los movimientos se ordenan:

```python
movimientos.sort(key=lambda m: m.fecha, reverse=True)  # más reciente primero
```

## Consentimiento

Para endosos, HU16 no permite confirmar sin `acepta_condiciones = true`, por lo que un endoso
registrado implica aceptación explícita. El historial expone `explicito`, `tipo`, `usuario_id`,
`rol`, `fecha` y `huella_solicitud`. No se exponen IP ni user-agent al cliente (mínimo
privilegio); quedan disponibles para una vista interna de auditoría futura.

## Información que NO se expone

`password_hash`, tokens JWT/refresh, `token_tarjeta`, `token_cuenta`, número completo de
tarjeta o cuenta, `idempotency_key`, IP y user-agent. La bitácora solo muestra identificadores
y referencias necesarios para la trazabilidad.

## Frontend

- Servicio: `web/src/services/historial-poliza.service.ts` (`obtenerHistorialPoliza`), usa
  `fetchAutenticado`.
- Tipos: `web/src/types/historial.ts`.
- Pantalla: `web/src/pages/HistorialPolizaPage.tsx`, ruta `/polizas/:polizaId/historial`,
  accesible desde el detalle de cada póliza en **Mis pólizas** con el botón "Ver historial".
  Reutiliza `AppLayout` y los estilos de `home.css`.

## Limitaciones actuales

HU25 solo muestra movimientos que realmente existan. No genera datos ficticios.

| Fuente | Estado |
|---|---|
| HU13 Pago inicial | Disponible |
| HU16 Endosos | Disponible |
| HU15 Desembolsos | Disponible |
| Cancelación (campo `cancelada_en`) | Disponible (básico) |
| HU17 Renovaciones | Pendiente de su HU; se integra cuando exista |
| HU18 Cancelaciones con entidad propia | Pendiente de su HU; de existir, se preferiría sobre el campo |
| HU21 Pagos periódicos | Pendiente de su HU |

El servicio (`app/polizas/historial.py`) está diseñado para agregar estas fuentes añadiendo un
método privado `_movimientos_*` y sumándolo en `_reunir`, sin cambiar el contrato público.
