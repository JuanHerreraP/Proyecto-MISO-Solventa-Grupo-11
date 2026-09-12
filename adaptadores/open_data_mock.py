import asyncio
import random
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Mock Adaptador Open Data - Solventa")

class OpenDataResponse(BaseModel):
    cliente_id: str
    score_territorial: float
    riesgo_zona: str
    latencia_simulada_ms: float

@app.get("/evaluar/{cliente_id}", response_model=OpenDataResponse)
async def evaluar_open_data(cliente_id: str, delay_ms: float = 60.0):
    """
    Simula la respuesta de fuentes abiertas de Open Data.
    Simula por defecto una latencia de ~60 ms.
    """
    # Simular latencia de respuesta de fuentes públicas
    await asyncio.sleep(delay_ms / 1000.0)
    
    seed = sum(ord(c) for c in cliente_id) + 1
    random.seed(seed)
    
    score = round(random.uniform(0.5, 0.90), 2)
    riesgo = "BAJO" if score > 0.7 else "MEDIO"
    
    return OpenDataResponse(
        cliente_id=cliente_id,
        score_territorial=score,
        riesgo_zona=riesgo,
        latencia_simulada_ms=delay_ms
    )