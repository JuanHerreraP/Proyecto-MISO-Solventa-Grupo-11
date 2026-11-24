# Caché Redis y alta disponibilidad

## Qué hace

Dos patrones de la vista de despliegue, que se apoyan uno en el otro:

- **Cache-Aside con Redis (ElastiCache).** Los datos que antes vivían en la memoria de un solo proceso (perfiles de riesgo, señales de las fuentes externas, último resultado de un enriquecimiento) pasan a una caché compartida. Se **lee primero la caché**; solo si no hay un dato fresco se consulta al origen.
- **Multi-AZ y autoescalado.** La base, la caché y el backend quedan repartidos en dos zonas de disponibilidad, y el backend suma o quita tareas según la carga.

Con más de una tarea del backend, todo lo que cada proceso guardaba en su memoria lo vería solo esa tarea. Por eso el patrón de caché es requisito del de disponibilidad.

## Qué pasa a ser compartido

| Dato | Antes | Ahora (en AWS) |
|---|---|---|
| Perfil de riesgo (lo lee el motor de precios) | Memoria del proceso | Redis, 1 hora |
| Señales de cada fuente externa, por cliente | Memoria del proceso | Redis, 24 horas |
| Último resultado del enriquecimiento | Memoria del proceso | Redis, 24 horas |
| Consentimientos | Memoria del proceso | Base de datos (`CONSENTIMIENTOS_EN_BD=true`) |
| Documentos (PDF de pólizas, evidencias) | Disco local con S3 como principal | Solo S3 (`ALMACEN_SOLO_S3=true`) |

El consentimiento va a la base y no a Redis porque es un registro que se debe conservar, no un dato que se pueda recalcular. El disco local de cada tarea se descarta en AWS: un documento guardado en una tarea no lo vería la otra.

## Cache-Aside: la caché primero

Al enriquecer, por cada fuente:

1. Se busca el dato en la caché. Si es más reciente que la **ventana de frescura** (`ENRIQUECIMIENTO_CACHE_FRESCURA_MINUTOS`, 60 por defecto con Redis), se usa **sin llamar al proveedor**. La traza lo marca como `CACHE` con el motivo `dato vigente en caché`.
2. Si no hay dato o ya no es fresco, se consulta al proveedor y se guarda el resultado.
3. Si el proveedor falla o tarda demasiado, se usa el último dato guardado aunque no sea fresco (EC12, ver [Enriquecimiento](enriquecimiento.md)).

Sin `REDIS_URL` el comportamiento es el anterior (proveedor primero, memoria del proceso): es el modo de desarrollo local y de las pruebas.

### Si Redis falla

Un fallo de Redis **nunca rompe una operación**. La lectura devuelve "no hay dato", la escritura se omite y se deja un aviso en el log. Efectos:

- **Enriquecimiento:** se consulta al proveedor como si no hubiera caché.
- **Cotización:** si el perfil no está, el motor de precios cotiza con la **tarifa base, sin personalizar** (`personalizada=false`). El precio no es incorrecto, pero el cliente pierde su ajuste por riesgo hasta que Redis vuelva y se genere de nuevo el perfil.
- **Último resultado:** no hay dato que mostrar al analista hasta el siguiente enriquecimiento.

## Alta disponibilidad

| Componente | Configuración |
|---|---|
| Base de datos | RDS PostgreSQL **Multi-AZ**: una réplica síncrona en la otra zona y cambio automático si falla la principal. Respaldos de 7 días |
| Caché | ElastiCache Redis con un nodo principal y una réplica en zonas distintas, **failover automático**, cifrado en reposo y en tránsito (`rediss://`) |
| Backend | `BackendDesiredCount` tareas (2 por defecto) repartidas en las dos subredes privadas. Despliegue gradual: nunca menos del 50 % en servicio |
| Autoescalado del backend | Entre `BackendDesiredCount` y `BackendMaxCount` (4). Mantiene el uso de CPU en 60 % y 200 solicitudes por tarea |
| Worker de telemetría | Con `EscalarWorkers=true` suma una tarea (hasta 4) cuando la cola pasa de 100 mensajes y la quita al vaciarse. Por defecto no escala, para poder demostrar la contrapresión de EC04 |
| Alertas | `PagosDlqAlarm` y `BackendUnhealthyAlarm` publican en `AlertasTopic`. Con `AlertasEmail` se suscribe un correo (hay que confirmar la suscripción) |

Se usa RDS PostgreSQL Multi-AZ y no Aurora: es el mismo motor que el resto del sistema, con la misma disponibilidad por zona y sin cambiar el código.

## Variables de entorno

| Variable | Dónde | Por defecto | Efecto |
|---|---|---|---|
| `REDIS_URL` | Backend | (vacía) | Activa Redis para perfiles, señales y último resultado. En AWS la entrega el stack |
| `ENRIQUECIMIENTO_CACHE_FRESCURA_MINUTOS` | Backend | `60` con Redis, `0` sin él | Minutos durante los que un dato de caché se usa sin consultar al proveedor |
| `CONSENTIMIENTOS_EN_BD` | Backend | `false` | `true` guarda los consentimientos en la base |
| `ALMACEN_SOLO_S3` | Backend | `false` | `true` no usa el disco: si S3 no está disponible, falla en vez de degradar |

## Infraestructura (`infra/aws/stack.json`)

| Recurso | Para qué |
|---|---|
| `Cache`, `CacheSubnets` y `CacheSg` | Grupo de replicación de Redis, sus subredes privadas y su grupo de seguridad (solo las tareas llegan al puerto 6379) |
| `Database` | `MultiAZ` activado y respaldos de 7 días |
| `Service` | `DesiredCount` según `BackendDesiredCount` |
| `BackendScalableTarget`, `BackendCpuPolicy` y `BackendRequestsPolicy` | Autoescalado del backend |
| `WorkerScalableTarget`, `WorkerScaleOutPolicy`, `WorkerScaleInPolicy`, `WorkerBacklogAlarm` y `WorkerIdleAlarm` | Autoescalado del worker de telemetría (solo con `EscalarWorkers=true`) |
| `AlertasTopic`, `AlertasSuscripcion` y `BackendUnhealthyAlarm` | Avisos de las alarmas |

El autoescalado usa el rol vinculado al servicio de Application Auto Scaling, que AWS crea la primera vez. La cuenta que despliega necesita permiso para crearlo.

Es una configuración **facturable**: la base Multi-AZ duplica la instancia, y Redis añade dos nodos `cache.t3.micro` y el backend una segunda tarea. Conviene eliminar el stack al terminar la demostración.

### Aprovisionar y eliminar

- El workflow **AWS Infra** crea todo con el stack y, después del despliegue, **verifica** que Redis esté disponible con failover automático y dos nodos, que la base sea Multi-AZ, cuántas tareas tiene el backend y que su autoescalado esté registrado.
- Al **eliminar**, el workflow anota el grupo de Redis, la base y el tópico de alertas antes de borrar el stack y, después, **comprueba que no quede nada**: si algo sobrevivió (un borrado interrumpido, por ejemplo), lo elimina. También borra todas las alarmas del stack y las que crea el autoescalado. Redis, la base y las alarmas no tienen política de retención. Ver `infra/aws/DESPLIEGUE.md`.

## Cómo probarlo

1. **Caché.** Con el stack desplegado, enriquece dos veces seguidas al mismo cliente: la segunda respuesta trae las fuentes con origen `CACHE` y el motivo `dato vigente en caché`, y el log del proveedor no registra una segunda consulta.
2. **Réplicas.** Registra un consentimiento y enriquece varias veces: todas las solicitudes funcionan sin importar qué tarea las atienda.
3. **Conmutación de la base (EC11).** En la consola de RDS, reinicia la base con **conmutación por error**. La API responde con errores breves (unos 60 a 120 segundos) y se recupera sola. El endpoint de la base no cambia.
4. **Caída de una tarea.** Detén una tarea del backend desde la consola de ECS: el balanceador deja de enviarle tráfico y ECS arranca otra.
5. **Autoescalado.** Genera carga contra la API (por ejemplo, con la prueba de carga del repositorio) y observa en ECS cómo `DesiredCount` sube hasta `BackendMaxCount` y baja al terminar.

La conmutación de la base, la caída de una tarea y el escalado se prueban a mano en AWS; la lógica de la caché y su tolerancia a fallos se prueban con pruebas automáticas.

## Pruebas automáticas

`backend/tests/enriquecimiento/test_cache_redis.py` (caché primero, ventana de frescura, dato compartido entre réplicas, Redis caído, dato ilegible, vencimiento y perfiles), `backend/tests/enriquecimiento/test_consentimientos_db.py` (consentimientos compartidos) y `backend/tests/emision/test_almacenamiento.py` (modo solo S3). Usan `fakeredis`.
