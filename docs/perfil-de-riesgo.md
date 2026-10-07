# Perfil de riesgo individualizado y pricing (HU11, BPM-57)

## Qué hace

Recibe las señales consolidadas de Open Finance y Open Data, calcula un puntaje de riesgo, emite el dictamen de suscripción y deja el resultado disponible para el motor de precios.

## Contrato de entrada (lo entrega la HU10)

`POST /api/v1/perfiles-riesgo`

```json
{
  "cliente_id": "CLI-001",
  "consentimiento_id": "CONS-001",
  "consentimiento_vigente": true,
  "open_finance": { "comportamiento_pago": 0.9, "nivel_endeudamiento": 0.2 },
  "open_data": { "estabilidad": 0.9, "riesgo_zona": "BAJO" },
  "origen": "FUENTES_EXTERNAS"
}
```

- Las señales numéricas van de 0 a 1. `riesgo_zona` es `BAJO`, `MEDIO` o `ALTO`. `origen` es `FUENTES_EXTERNAS` o `CACHE`.
- El contrato no admite campos adicionales: lo propio de cada proveedor se queda en su adaptador (EC14).

## Endpoints

| Método y ruta | Quién | Devuelve |
|---|---|---|
| `POST /api/v1/perfiles-riesgo` | Servicio interno, Asesor de Ventas | Perfil completo |
| `GET /api/v1/perfiles-riesgo/{cliente_id}` | Analista de Riesgos, servicio interno | Perfil completo con puntaje y reglas aplicadas |
| `GET /api/v1/perfiles-riesgo/{cliente_id}/oferta` | Cualquier rol identificado | Dictamen, extraprima y explicación, sin reglas internas |

Todas las respuestas llevan la cabecera `X-Tiempo-Proceso-Ms`.

## Reglas (versión 1.0.0)

**Puntaje de riesgo**, de 0 (mínimo) a 100 (máximo):

- Riesgo financiero = 60 % × (1 − comportamiento de pago) + 40 % × endeudamiento.
- Riesgo de entorno = 70 % × (1 − estabilidad) + 30 % × riesgo de zona (BAJO 0,1; MEDIO 0,5; ALTO 0,9).
- Puntaje = 100 × (60 % × riesgo financiero + 40 % × riesgo de entorno).

**Clasificación:** BAJO por debajo de 30, MEDIO de 30 a 69, ALTO desde 70.

**Dictamen**

| Condición | Dictamen |
|---|---|
| Endeudamiento ≥ 90 %, comportamiento de pago < 20 % o puntaje ≥ 85 | RECHAZADO |
| Puntaje de 60 a 84 | AJUSTADO, con extraprima de 10 % más 1 punto por cada punto sobre 60 (máximo 34 %) |
| Puntaje menor a 60 | ACEPTADO, tarifa estándar |

**Factor para el motor de precios:** 0,8 + 0,7 × puntaje / 100. Va de 0,8 (descuento) a 1,5 (recargo), el mismo rango que usó el Experimento 1.

Los pesos y umbrales son valores iniciales definidos por el equipo de desarrollo; no vienen de un modelo actuarial. Están como constantes en `backend/app/perfilamiento/dominio/reglas.py` y cualquier cambio debe subir `VERSION_REGLAS`.

## Pendientes conocidos

- **Autenticación:** el rol se lee de la cabecera `X-Rol` de forma provisional. Debe reemplazarse por el rol del token cuando la HU19 (BPM-54) esté lista. Hasta entonces tampoco se puede comprobar que un cliente consulte solo su propia oferta.
- **Persistencia:** el perfil se guarda en memoria con vigencia de una hora, detrás del puerto `RepositorioPerfiles`. Falta el adaptador de ElastiCache Redis.
- **EC02:** el script `backend/tests/k6/perfil_riesgo.js` trae los umbrales p95 ≤ 400 ms y p99 ≤ 800 ms, pero no se ha corrido contra un ambiente desplegado. La prueba local solo mide el cálculo en proceso.
- **Integración con la HU10:** conectada. `POST /api/v1/enriquecimientos` consolida las señales y genera el perfil con este contrato. Ver [enriquecimiento.md](enriquecimiento.md).
