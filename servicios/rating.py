import os
import time
from typing import Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
import httpx

app = FastAPI(
    title="Servicio de Cotización y Precio (Rating Engine) - Solventa",
    version="1.0.0"
)

# URL del Servicio de Perfilamiento de Riesgo
PERFILAMIENTO_SERVICE_URL = os.getenv(
    "PERFILAMIENTO_SERVICE_URL", 
    "http://localhost:8000/api/v1/perfilamiento"
)

# Modelos de Solicitud y Respuesta
class CotizacionRequest(BaseModel):
    cliente_id: str
    monto_credito: float = Field(..., gt=0, description="Monto del crédito hipotecario")
    plazo_meses: int = Field(240, gt=0, description="Plazo del crédito en meses")
    ramo: str = Field("VIDA_HIPOTECARIO", description="Ramo del seguro")

class CotizacionResponse(BaseModel):
    cotizacion_id: str
    cliente_id: str
    ramo: str
    monto_credito: float
    prima_mensual: float
    score_riesgo: float
    nivel_riesgo: str
    fuente_perfilamiento: str
    tiempo_ejecucion_ms: float

@app.post("/api/v1/cotizar", response_model=CotizacionResponse, status_code=status.HTTP_201_CREATED)
async def calcular_cotizacion(payload: CotizacionRequest):
    start_time = time.perf_counter()
    
    # 1. Obtenemos el perfil de riesgo invocando el Servicio de Perfilamiento
    async with httpx.AsyncClient(timeout=1.0) as client:
        try:
            response = await client.get(f"{PERFILAMIENTO_SERVICE_URL}/{payload.cliente_id}")
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Error obteniendo el perfil de riesgo del cliente."
                )
            perfil = response.json()
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Fallo de conexión con el servicio de perfilamiento: {str(exc)}"
            )

    score_riesgo = perfil.get("score_riesgo", 0.5)
    nivel_riesgo = perfil.get("nivel_riesgo", "MEDIO")
    fuente_perfil = perfil.get("fuente", "desconocido")

    # 2. Regla Actuarial de Tarifación (Rating Formula)
    # Tasa base anual: 0.15% del monto del crédito
    tasa_base_anual = 0.0015
    prima_base_mensual = (payload.monto_credito * tasa_base_anual) / 12

    # Factor de ajuste por riesgo individualizado (Open Finance / Open Data)
    # Score 0.0 -> Factor 0.8 (Descuento por buen riesgo)
    # Score 1.0 -> Factor 1.5 (Recargo por alto riesgo)
    factor_riesgo = 0.8 + (score_riesgo * 0.7)
    
    factor_plazo = payload.plazo_meses / 240
    prima_final_mensual = round(
        prima_base_mensual * factor_riesgo * factor_plazo,
        2
    )
    
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    
    # 3. Construcción del resultado de cotización
    cotizacion_id = f"COT-{payload.cliente_id[:6]}-{int(time.time())}"

    return CotizacionResponse(
        cotizacion_id=cotizacion_id,
        cliente_id=payload.cliente_id,
        ramo=payload.ramo,
        monto_credito=payload.monto_credito,
        prima_mensual=prima_final_mensual,
        score_riesgo=score_riesgo,
        nivel_riesgo=nivel_riesgo,
        fuente_perfilamiento=fuente_perfil,
        tiempo_ejecucion_ms=elapsed_ms
    )