// Prueba de carga de HU03 frente a EC01 (p95 <= 250 ms, p99 <= 500 ms).
//
// Requisitos:
// - Socio activo con el endpoint `cotizaciones:crear` y sus credenciales OAuth.
// - CLIENTE_ID con consentimiento vigente y perfil generado desde Open Finance/Open Data.
//
// Uso:
//   k6 run \
//     -e BASE_URL=https://<host-del-servicio> \
//     -e CLIENT_ID=<client-id> \
//     -e CLIENT_SECRET=<client-secret> \
//     -e CLIENTE_ID=<cliente-con-perfil> \
//     backend/tests/k6/cotizaciones.js
import encoding from "k6/encoding";
import http from "k6/http";
import { check } from "k6";
import { Rate, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const CLIENTE_ID = __ENV.CLIENTE_ID;

const duracionCotizacion = new Trend("cotizacion_duration", true);
const cotizacionFallida = new Rate("cotizacion_failed");

export const options = {
  scenarios: {
    cotizacion_embebida: {
      executor: "constant-arrival-rate",
      rate: Number(__ENV.TASA || 50),
      timeUnit: "1s",
      duration: __ENV.DURACION || "1m",
      preAllocatedVUs: Number(__ENV.VUS_INICIALES || 50),
      maxVUs: Number(__ENV.VUS_MAXIMOS || 200),
    },
  },
  thresholds: {
    cotizacion_duration: ["p(95)<=250", "p(99)<=500"],
    cotizacion_failed: ["rate<0.01"],
    checks: ["rate>0.99"],
  },
};

export function setup() {
  if (!CLIENTE_ID) {
    throw new Error("Debe definir CLIENTE_ID con perfil y consentimiento vigentes.");
  }
  if (__ENV.PARTNER_TOKEN) {
    return { token: __ENV.PARTNER_TOKEN };
  }
  if (!__ENV.CLIENT_ID || !__ENV.CLIENT_SECRET) {
    throw new Error("Debe definir CLIENT_ID y CLIENT_SECRET, o PARTNER_TOKEN.");
  }

  const credenciales = encoding.b64encode(`${__ENV.CLIENT_ID}:${__ENV.CLIENT_SECRET}`);
  const respuesta = http.post(
    `${BASE_URL}/api/v1/oauth/token`,
    "grant_type=client_credentials",
    {
      headers: {
        Authorization: `Basic ${credenciales}`,
        "Content-Type": "application/x-www-form-urlencoded",
      },
    },
  );

  if (respuesta.status !== 200) {
    throw new Error(`No fue posible autenticar al socio: HTTP ${respuesta.status}.`);
  }
  return { token: respuesta.json("access_token") };
}

export default function (datos) {
  const cuerpo = JSON.stringify({
    cliente_id: CLIENTE_ID,
    ramo: "VIAJE",
    datos_riesgo: {
      destino: "Lima",
      fecha_inicio: "2027-01-10",
      fecha_fin: "2027-01-20",
      numero_viajeros: 2,
      valor_asegurado: 15000000,
    },
  });

  const respuesta = http.post(`${BASE_URL}/api/v1/cotizaciones`, cuerpo, {
    headers: {
      Authorization: `Bearer ${datos.token}`,
      "Content-Type": "application/json",
    },
    tags: { escenario: "EC01" },
  });
  duracionCotizacion.add(respuesta.timings.duration);

  const exitosa = check(respuesta, {
    "responde 201": (r) => r.status === 201,
    "retorna precio": (r) => Number(r.json("prima_total")) > 0,
    "aplica perfil Open Finance/Open Data": (r) => r.json("perfil_riesgo_id") !== null,
    "conserva aislamiento del socio": (r) => Boolean(r.json("socio_id") && r.json("tenant_id")),
  });
  cotizacionFallida.add(!exitosa);
}
