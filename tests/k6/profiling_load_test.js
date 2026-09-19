import http from 'k6/http';
import { check } from 'k6';
import { Trend } from 'k6/metrics';

// Métrica personalizada para auditar el p95
const latenciaCotizacion = new Trend('latencia_cotizacion', true);

// IMPORTANTE: Sobrescribir con la DNS pública de tu ALB (Puerto 80)
const BASE_URL = __ENV.BASE_URL || 'http://tu-alb-ec03.us-east-2.elb.amazonaws.com';

export const options = {
    scenarios: {
        ec03_escalabilidad: {
            executor: 'ramping-arrival-rate',
            startRate: 8,               // ~500 cotizaciones/minuto (8.33 req/s)
            timeUnit: '1s',
            preAllocatedVUs: 200,        // VUs reservadas para la rampa
            maxVUs: 3000,                // VUs máximas para sostener las 833.33 req/s
            stages: [
                { duration: '30s', target: 8 },     // Baseline: 500 cotizaciones/minuto
                { duration: '1m',  target: 834 },   // Disparo violento a 50.000 req/min (~834 req/s) en <= 60s
                { duration: '3m',  target: 834 },   // Sostiene las 50.000 req/min para validar p95 en régimen permanente
                { duration: '1m',  target: 8 },     // Rampa de bajada (cooldown)
            ],
            exec: 'cotizarService',
        },
    },

    // Criterios de aceptación del experimento EC03
    thresholds: {
        // Exigencia del p95 de latencia
        latencia_cotizacion: ['p(95)<1000'], // Ajusta a tu SLA objetivo (ej. < 1000ms)
        
        // Tasa de error general aceptable durante el escalado
        http_req_failed: ['rate<0.02'],      // Menos del 2% de errores durante la transición de Auto Scaling
    },
};

const headers = {
    'Content-Type': 'application/json',
};

function payload(clienteId) {
    return JSON.stringify({
        cliente_id: clienteId,
        monto_credito: 250000000,
        plazo_meses: 240,
        ramo: 'VIDA_HIPOTECARIO',
    });
}

export function cotizarService() {
    // Genera clientes dinámicos para evitar respuestas cacheables si se requiere evaluar cómputo real
    const clienteId = `k6-ec03-${__VU}-${__ITER}-${Date.now()}`;

    const response = http.post(
        `${BASE_URL}/api/v1/cotizar`,
        payload(clienteId),
        { headers }
    );

    // Registrar latencia de la petición
    latenciaCotizacion.add(response.timings.duration);

    check(response, {
        'Estado 201 o 200 (Cotización exitosa)': (r) => r.status === 201 || r.status === 200,
    });
}