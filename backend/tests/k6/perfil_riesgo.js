// Prueba de desempeño de la HU11 frente a EC02 (p95 <= 400 ms, p99 <= 800 ms).
//
// Uso:
//   k6 run -e BASE_URL=https://<host-del-servicio> backend/tests/k6/perfil_riesgo.js
//
// Mide la generación del perfil a partir de señales ya consolidadas. El recorrido completo
// de EC02 incluye además la consulta a Open Finance y Open Data (HU10).
import http from "k6/http";
import { check } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

export const options = {
  scenarios: {
    perfilamiento: {
      executor: "constant-arrival-rate",
      rate: Number(__ENV.TASA || 50),
      timeUnit: "1s",
      duration: __ENV.DURACION || "1m",
      preAllocatedVUs: 50,
      maxVUs: 200,
    },
  },
  thresholds: {
    http_req_duration: ["p(95)<=400", "p(99)<=800"],
    http_req_failed: ["rate<0.01"],
    checks: ["rate>0.99"],
  },
};

export default function () {
  const cuerpo = JSON.stringify({
    cliente_id: `CLI-${__VU}-${__ITER}`,
    consentimiento_id: "CONS-K6",
    consentimiento_vigente: true,
    open_finance: {
      comportamiento_pago: Math.random(),
      nivel_endeudamiento: Math.random() * 0.85,
    },
    open_data: {
      estabilidad: Math.random(),
      riesgo_zona: ["BAJO", "MEDIO", "ALTO"][__ITER % 3],
    },
    origen: "FUENTES_EXTERNAS",
  });

  const respuesta = http.post(`${BASE_URL}/api/v1/perfiles-riesgo`, cuerpo, {
    headers: { "Content-Type": "application/json", "X-Rol": "SERVICIO_INTERNO" },
  });

  check(respuesta, {
    "responde 201": (r) => r.status === 201,
    "trae dictamen": (r) => ["ACEPTADO", "AJUSTADO", "RECHAZADO"].includes(r.json("dictamen")),
  });
}
