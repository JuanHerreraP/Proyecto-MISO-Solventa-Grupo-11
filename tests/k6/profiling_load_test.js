import http from 'k6/http';
import { check } from 'k6';
import { Trend } from 'k6/metrics';

const cacheHitDuration = new Trend('cache_hit_duration', true);
const cacheMissDuration = new Trend('cache_miss_duration', true);

const BASE_URL = __ENV.BASE_URL || 'http://18.217.232.244:8003';

export const options = {
    scenarios: {
        cache_hit: {
            executor: 'constant-vus',
            exec: 'cacheHit',
            vus: 5,
            duration: '30s',
        },

        cache_miss: {
            executor: 'constant-vus',
            exec: 'cacheMiss',
            vus: 5,
            duration: '30s',
            startTime: '35s',
        },
    },

    thresholds: {
        cache_hit_duration: [
            'p(95)<400',
            'p(99)<800',
        ],

        cache_miss_duration: [
            'p(95)<400',
            'p(99)<800',
        ],

        http_req_failed: [
            'rate<0.01',
        ],
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


// -------------------------------------------------
// Preparar un cliente que quede previamente en Redis
// -------------------------------------------------

export function setup() {
    const clienteId = 'k6-cliente-cache';

    const response = http.post(
        `${BASE_URL}/api/v1/cotizar`,
        payload(clienteId),
        { headers }
    );

    check(response, {
        'warmup responde 201': (r) => r.status === 201,
    });

    return {
        clienteCache: clienteId,
    };
}


// -------------------------------------------------
// CACHE HIT
// Se reutiliza siempre el mismo cliente.
// -------------------------------------------------

export function cacheHit(data) {
    const response = http.post(
        `${BASE_URL}/api/v1/cotizar`,
        payload(data.clienteCache),
        { headers }
    );

    cacheHitDuration.add(response.timings.duration);

    check(response, {
        'cache hit - HTTP 201': (r) => r.status === 201,

        'respuesta viene de cache': (r) => {
            try {
                return r.json('fuente_perfilamiento') === 'cache';
            } catch (_) {
                return false;
            }
        },
    });
}


// -------------------------------------------------
// CACHE MISS
// Cada petición utiliza un cliente nuevo.
// -------------------------------------------------

export function cacheMiss() {
    const clienteId =
        `k6-miss-${__VU}-${__ITER}-${Date.now()}`;

    const response = http.post(
        `${BASE_URL}/api/v1/cotizar`,
        payload(clienteId),
        { headers }
    );

    cacheMissDuration.add(response.timings.duration);

    check(response, {
        'cache miss - HTTP 201': (r) => r.status === 201,

        'respuesta viene de proveedor externo': (r) => {
            try {
                return (
                    r.json('fuente_perfilamiento')
                    === 'external_fetch'
                );
            } catch (_) {
                return false;
            }
        },
    });
}
