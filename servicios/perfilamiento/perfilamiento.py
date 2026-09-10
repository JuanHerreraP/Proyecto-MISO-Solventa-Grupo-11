import json
import os
import asyncio
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import redis.asyncio as redis
import httpx

app = FastAPI(title="Servicio de Perfilamiento de Riesgo - Solventa")

# Configuración de entornos y conectores
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
OPEN_FINANCE_URL = os.getenv("OPEN_FINANCE_URL", "http://mock-open-finance/evaluar")
OPEN_DATA_URL = os.getenv("OPEN_DATA_URL", "http://mock-open-data/evaluar")
CACHE_TTL_SECONDS = 3600  # 1 hora de vigencia del perfil

# Cliente de Redis asíncrono
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

class PerfilRiesgoResponse(BaseModel):
    cliente_id: str
    score_riesgo: float
    nivel_riesgo: str
    fuente: str  # "cache" o "external_fetch"

@app.get("/api/v1/perfilamiento/{cliente_id}", response_model=PerfilRiesgoResponse)
async def obtener_perfil_riesgo(cliente_id: str):
    cache_key = f"perfil:{cliente_id}"
    
    # PASO 1: Consultar la caché (Cache-Aside)
    try:
        cached_profile = await redis_client.get(cache_key)
        if cached_profile:
            data = json.loads(cached_profile)
            data["fuente"] = "cache"
            return data
    except Exception as e:
        # Fallback en caso de error de conexión a Redis (degradación elegante)
        pass

    # PASO 2: Cache Miss -> Consultar adaptadores de Open Finance y Open Data
    async with httpx.AsyncClient(timeout=0.7) as client: # Timeout duro de 700 ms
        try:
            # Consultas en paralelo a los adaptadores Lambda
            res_finance, res_data = await asyncio.gather(
                client.get(f"{OPEN_FINANCE_URL}/{cliente_id}"),
                client.get(f"{OPEN_DATA_URL}/{cliente_id}"),
                return_exceptions=True
            )
            
            # Procesar respuestas externas (simuladas o reales)
            score_finance = res_finance.json().get("score", 0.5) if not isinstance(res_finance, Exception) and res_finance.status_code == 200 else 0.5
            score_data = res_data.json().get("score", 0.5) if not isinstance(res_data, Exception) and res_data.status_code == 200 else 0.5
            
            # Consolidar scoring de riesgo
            final_score = round((score_finance * 0.6) + (score_data * 0.4), 2)
            nivel = "BAJO" if final_score < 0.3 else "MEDIO" if final_score < 0.7 else "ALTO"
            
            perfil_consolidado = {
                "cliente_id": cliente_id,
                "score_riesgo": final_score,
                "nivel_riesgo": nivel
            }

            # PASO 3: Guardar el resultado en ElastiCache Redis con TTL
            await redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(perfil_consolidado))
            
            perfil_consolidado["fuente"] = "external_fetch"
            return perfil_consolidado

        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Error consultando fuentes externas de perfilamiento: {str(err)}"
            )
