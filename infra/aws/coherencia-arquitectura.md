# Coherencia del despliegue con la wiki

Revisión del 17 de octubre de 2026 sobre la wiki en el commit
`96c7ac0ec72e9e4eb4426701c462c72389e1b982` y el código de esta rama.
La wiki se consultó en modo lectura; no se modificaron páginas remotas.

## Fuentes y alcance

- [Modelos de Arquitectura, vista de despliegue](https://github.com/JuanHerreraP/Proyecto-MISO-Solventa-Grupo-11/wiki/Modelos-de-Arquitectura#3-vista-de-despliegue): arquitectura objetivo y conexiones.
- [Semana 8](https://github.com/JuanHerreraP/Proyecto-MISO-Solventa-Grupo-11/wiki/Semana-8): consolidación del diseño con Aurora Multi-AZ, Redis, mensajería y Lambda.
- [Semana 10](https://github.com/JuanHerreraP/Proyecto-MISO-Solventa-Grupo-11/wiki/Semana-10): alcance funcional del Sprint 1, seis HU.
- [Frameworks y Ambientes](https://github.com/JuanHerreraP/Proyecto-MISO-Solventa-Grupo-11/wiki/Semana-3-‐-4.-Frameworks-y-Ambientes): S3 + CloudFront para estáticos y RDS PostgreSQL Multi-AZ.
- [BFF Web y Android](https://github.com/JuanHerreraP/Proyecto-MISO-Solventa-Grupo-11/wiki/Patrón-2:-Backend-for-Frontend-para-web-y-Android): permite fachadas inicialmente dentro de un mismo despliegue.
- [Experimento 2](https://github.com/JuanHerreraP/Proyecto-MISO-Solventa-Grupo-11/wiki/Resultados-Experimento-2-‐-Escalabilidad-del-servicio-de-cotización): hallazgo sobre servicios co-ubicados y propuesta de desacoplamiento con SQS.
- [Prácticas CI/CD](https://github.com/JuanHerreraP/Proyecto-MISO-Solventa-Grupo-11/wiki/Prácticas-CI-CD): CI implementada; CD AWS pendiente.

La página antigua de ambientes habla de RDS PostgreSQL y la consolidación
posterior precisa Aurora PostgreSQL. Se usa Aurora, que forma parte de RDS,
con una segunda instancia en otra zona para failover. No se tratan las seis
HU terminadas como evidencia de que toda la arquitectura esté implementada.

## Comparación y decisiones

| Elemento de la wiki | Plantilla y código del MVP | Estado / consecuencia |
|---|---|---|
| API Gateway → ALB → Fargate | HTTP API con throttling y logs, VPC Link y ALB interno hacia FastAPI | Implementado en IaC; autorización todavía en la aplicación |
| Acceso público HTTPS | CloudFront sin dominio propio → API Gateway HTTPS | Implementado en IaC; HTTP solo en integración privada ALB/API |
| Cómputo privado | ECS sin IP pública, dos subredes de aplicación y NAT por AZ | Implementado en IaC; NAT implica costo fijo |
| Web estática S3 + CloudFront | Bucket privado con OAC, versionamiento y reescritura de rutas React | Implementado en IaC; publicación de estáticos separada de ECS |
| Aurora PostgreSQL Multi-AZ | Clúster Serverless v2 y dos instancias en distintas AZ, endpoint writer, TLS, backups | Implementado en IaC; pendiente prueba real de failover/RTO/RPO |
| Identidad/KYC, socios, riesgo y enriquecimiento | Módulos existentes en una API FastAPI | Se conserva el empaquetamiento actual; no se presenta como microservicios independientes |
| BFF Web y BFF Móvil | Sesión web con cookies/CSRF y endpoints de tokens Android en la misma API | Parcial: no existen las fachadas completas del diseño objetivo |
| Adaptadores externos Lambda | Adaptadores Python en proceso; KYC A/B/C como contenedores simulados | Pendiente Lambda y proveedores reales; no se aprovisionan funciones sin consumidor |
| Cache-Aside con ElastiCache | Caché de señales y perfiles en memoria | Pendiente adaptador Redis; no se crea un clúster que el código no utiliza |
| Persistencia de consentimientos | `RepositorioConsentimientosEnMemoria` | Brecha del código: se pierden al reiniciar; requiere persistencia transaccional |
| Réplicas y autoescalado ECS | `DesiredCount=1`, un proceso, sin política de escalado | Pendiente sacar el estado de memoria; dos subredes disponibles no significan dos réplicas |
| Cotización → SQS → perfilamiento | No hay servicio de cotización ni productor/consumidor SQS en esta versión | Pendiente implementación del flujo; no se reproduce el escenario experimental ni se afirma EC03 |
| SNS/SQS, pagos y telemetría | No existen esos procesos en el Sprint 1 actual | Se posponen hasta implementar sus consumidores, idempotencia y DLQ |
| S3 para evidencias | Bucket de activos web solamente | Evidencias requieren bucket y políticas propios cuando exista siniestros |
| CI/CD | GitHub Actions CI; publicación AWS manual reproducible | Coincide con el estado del Sprint 1 documentado; CD pendiente |
| Offline y capacidades Android | APK consume la URL HTTPS; biometría permanece en dispositivo | Desplegar el backend no implementa sincronización offline ni push pendientes |

“Implementado en IaC” significa definido en la plantilla, **no desplegado ni
validado en una cuenta AWS**. CloudFormation, imágenes y flujos completos deben
validarse en el entorno real antes de considerar la entrega operativa.

## Qué se corrigió respecto de la primera propuesta de esta rama

La propuesta inicial omitía API Gateway, ejecutaba la web dentro de la tarea
ECS, usaba PostgreSQL Single-AZ y un ALB público detrás de CloudFront. La
plantilla revisada incorpora API Gateway con integración privada, separa los
estáticos en S3 y configura Aurora con dos instancias. Se retira el secreto de
cabecera de origen porque el ALB ahora es interno y su SG solo admite el VPC Link.
El tramo CloudFront → API Gateway queda cifrado sin comprar dominio.

El experimento 2 desaconseja presentar un grupo de servicios co-ubicados como
solución de escalabilidad. Aquí quedan co-ubicados solo la API actual y los
dobles KYC, para una demo funcional. Separar web y API reduce ese acoplamiento,
pero no resuelve las limitaciones de escalado de los dominios existentes.
Los sidecars KYC se reemplazarán al integrar proveedores reales.

## Condiciones para cerrar las brechas

1. Persistir consentimientos, perfiles que deban conservarse y estado de tenants
   según sus requisitos; conectar ElastiCache para caché/estado temporal con TTL.
   Redis no reemplaza la persistencia transaccional del consentimiento.
2. Con estado externo, habilitar al menos dos réplicas ECS en AZ distintas,
   despliegues sin interrupción y autoescalado; probar consistencia entre réplicas.
3. Al implementar cotización, añadir productor/consumidor SQS, idempotencia,
   DLQ y métricas de profundidad/edad; probar el flujo asíncrono antes de prometer EC03.
4. Extraer servicios y adaptadores Lambda a medida que existan contratos y
   ejecutables independientes; mantener las interfaces web/Android estables.
5. Medir EC01/EC02/EC03 y failover EC11 en AWS. No extrapolar las pruebas
   unitarias ni los resultados de prototipos a este despliegue.

Para la demo actual, usar datos sintéticos y explicar la pérdida de estado en
memoria. El despliegue puede soportar las funcionalidades actuales, pero **no
representa cumplimiento integral de la arquitectura objetivo ni de sus ASR**.

## Validación de esta revisión

Las dos plantillas pasan `cfn-lint 1.57.2` para `us-east-1`, incluida la
validación de esquemas, referencias y dependencias. CI incorpora el mismo
chequeo. La función de rutas SPA se ejecutó con Node para `/`, `/login`,
`/admin/socios/nuevo` y dos activos con extensión; la API no asocia esa función.
La web compila correctamente con Vite.

Faltan la creación real en AWS, construcción/exportación con Docker, carga de
S3, conectividad API Gateway/ALB/ECS/Aurora, validación funcional con PostgreSQL
y pruebas de recuperación y carga. El lint no comprueba permisos, cuotas,
disponibilidad regional de la versión Aurora ni el comportamiento operativo.
