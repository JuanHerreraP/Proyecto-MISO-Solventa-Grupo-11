# GitHub Copilot Agent Rules: Solventa - Experimento 1 (Cache-Aside & Latencia EC02)

## 🎯 Contexto y Objetivo del Proyecto
Eres un agente de inteligencia artificial experto en arquitectura de software y desarrollo en **Python (FastAPI)** para **Solventa**, una aseguradora digital (insurtech) nativa en la nube basada en Finanzas Abiertas (Open Finance) y Datos Abiertos (Open Data) en Colombia.

Tu objetivo principal es asistir en la implementación del **Experimento 1: Validación de latencia del perfilamiento mediante Cache-Aside**, garantizando el cumplimiento estricto de las decisiones de arquitectura y los atributos de calidad del proyecto.

---

## 📊 Atributo de Calidad y Metas de Rendimiento (ASR)
- **Escenario Objetivo (EC02 - Latencia)**: Perfilamiento de riesgo individualizado y personalización de oferta dentro del recorrido de compra del seguro de vida hipotecario.
- **Límites Máximos de Latencia (Extremo a Extremo)**:
  - **p95 ≤ 400 ms**
  - **p99 ≤ 800 ms**
- **Presupuesto por Dependencia Externa**:
  - Tiempo de respuesta objetivo: **≤ 120 ms** por llamada externa.
  - Timeout duro de corte: **700 ms**.

---

## 🏗️ Patrón y Componentes de Arquitectura

### 1. Patrón: Cache-Aside (Patrón 6)
- El microservicio de **Perfilamiento de Riesgo** debe consultar primero el perfil de riesgo en **ElastiCache Redis**.
- **Cache Hit**: Retornar inmediatamente el perfil existente desde la caché sin invocar adaptadores externos.
- **Cache Miss**: Invocar asíncronamente los adaptadores de **Open Finance** y **Open Data** (AWS Lambda), consolidar el perfil de riesgo, guardarlo en Redis con un TTL adecuado y retornar la respuesta.
- **Degradación Elegante**: Si un proveedor externo falla o supera el timeout de 700 ms, se debe degradar con un valor por defecto o perfil previamente cacheado sin exceder el presupuesto total del journey.

### 2. Matriz de Componentes y Tecnologías
| Componente | Propósito | Tecnología / Entorno |
| :--- | :--- | :--- |
| **Perfilamiento de Riesgo** | Generar el perfil de riesgo individualizado del cliente usando Cache-Aside | Python 3.12+ / FastAPI / AWS ECS Fargate |
| **Cotización y Precio** | Calcular la prima personalizada consumiendo el perfil de riesgo | Python 3.12+ / FastAPI / AWS ECS Fargate |
| **Adaptador Open Finance** | Mapear solicitudes al contrato del proveedor de Open Finance | Python 3.12+ / AWS Lambda |
| **Adaptador Open Data** | Mapear solicitudes al contrato de fuentes de Open Data | Python 3.12+ / AWS Lambda |
| **Almacenamiento de Caché** | Caché en memoria para perfiles de riesgo y cotizaciones | ElastiCache Redis (`redis-py`) |
| **Proveedores Simulados** | Mocks/Stubs con latencia controlada para pruebas | Python / FastAPI Mocks |
| **Pruebas de Carga** | Medición de percentiles p95 y p99 bajo tráfico | k6 |
| **Pruebas Automatizadas** | Pruebas unitarias e integración de flujos de caché | `pytest` + `pytest-asyncio` |

---

## 🛠️ Reglas de Implementación y Estándares de Código

### A. Estándares de Python & FastAPI
1. Todo el código de endpoints e integraciones de I/O debe ser estrictamente **asíncrono (`async / await`)**.
2. Utilizar modelos **Pydantic v2** para validación, serialización y esquemas de entrada/salida.
3. Mantener una separación limpia de capas (Clean Architecture):
   - `domain/`: Entidades del dominio y reglas de cálculo de riesgo.
   - `services/`: Lógica de negocio (ej. `RiskProfilingService` aplicando Cache-Aside).
   - `adapters/`: Clientes para Redis, Open Finance y Open Data.
   - `api/`: Enrutadores de FastAPI y controladores HTTP.

### B. Protocolo de Caché (`redis-py`)
- Usar el cliente asíncrono `redis.asyncio.Redis`.
- Formato de clave estandarizado: `solventa:risk_profile:{customer_id}`.
- Manejar excepciones de conexión a Redis para que, en caso de falla de la caché, el sistema continúe operando mediante consulta directa (sin tumbar la aplicación).

### C. Resiliencia y Control de Latencias
- Configurar clientes HTTP con `httpx.AsyncClient` aplicando timeouts estrictos:
  ```python
  timeout = httpx.Timeout(timeout=0.7, connect=0.12)  # 700 ms timeout duro, 120 ms conexión
  ```
- Implementar mecanismos de reintento y fallback cuando el tiempo limite sea superado.

### D. Automatización de Pruebas (`pytest` + `pytest-asyncio`)
Crear suites de prueba para validar automáticamente los 4 escenarios clave:
1. **Cache Hit**: Perfil existe en Redis → No se invocan adaptadores externos.
2. **Cache Miss**: Perfil no existe → Se llaman adaptadores, se genera perfil y se guarda en Redis.
3. **Expiración de Caché**: La clave expira → Se ejecuta un nuevo fetch a adaptadores.
4. **Respuesta de Adaptador Degradada**: Timeout o error 50x del proveedor simulado → Se activa fallback sin romper el servicio.

---

## 📊 Configuración de Pruebas de Carga (k6)
- Ubicar los scripts de prueba en `tests/k6/profiling_load_test.js`.
- Configurar los umbrales (*thresholds*) de aprobación alineados con **EC02**:
  ```javascript
  export const options = {
    thresholds: {
      http_req_duration: ['p(95)<400', 'p(99)<800'],
    },
  };
  ```

---

## 📁 Estructura del Repositorio Sugerida
```text
.
├── services/
│   ├── profiling/             # Servicio de Perfilamiento de Riesgo (FastAPI)
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   ├── domain/
│   │   │   ├── services/
│   │   │   └── adapters/
│   │   └── tests/
│   └── rating/                # Servicio de Cotización y Precio (FastAPI)
├── lambdas/
│   ├── open_finance_adapter/  # Adaptador Open Finance (AWS Lambda)
│   └── open_data_adapter/     # Adaptador Open Data (AWS Lambda)
├── mocks/                     # Mocks/Stubs de servicios externos
├── tests/
│   └── k6/                    # Scripts de k6 para medición de latencia
├── .github/
│   └── copilot-instructions.md
└── docker-compose.yml
```
