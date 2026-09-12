import asyncio
import random
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Mock Adaptador Open Finance - Solventa")

class OpenFinanceResponse(BaseModel):
    cliente_id: str
    score_financiero: float
    capacidad_pago: float
    historial_credito: str
    latencia_simulada_ms: float

@app.get("/evaluar/{cliente_id}", response_model=OpenFinanceResponse)
async def evaluar_open_finance(cliente_id: str, delay_ms: float = 80.0):
    """
    Simula la respuesta de Open Finance. 
    Permite parametrizar el delay para probar respuestas dentro del presupuesto (<= 120 ms) 
    o inducir latencia/timeouts.
    """
    # Simular latencia de red del proveedor externo (por defecto ~80 ms)
    await asyncio.sleep(delay_ms / 1000.0)
    
    # Generar score sintético basado en el cliente_id para consistencia en pruebas
    seed = sum(ord(c) for c in cliente_id)
    random.seed(seed)
    
    score = round(random.uniform(0.6, 0.95), 2)
    capacidad = round(random.uniform(2000000, 10000000), 2)
    
    return OpenFinanceResponse(
        cliente_id=cliente_id,
        score_financiero=score,
        capacidad_pago=capacidad,
        historial_credito="ALTO_CUMPILIMIENTO",
        latencia_simulada_ms=delay_ms
    )