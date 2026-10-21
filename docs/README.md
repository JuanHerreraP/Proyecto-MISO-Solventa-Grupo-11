# Documentación técnica

## Qué contiene

Documentos que acompañan la implementación de Solventa: comportamiento, flujos,
contratos de API, permisos, configuración y pruebas. La arquitectura y las entregas
se mantienen en la [wiki del proyecto](https://github.com/JuanHerreraP/Proyecto-MISO-Solventa-Grupo-11/wiki).

## Identidad, sesión y control de acceso

| Documento | Contenido |
| --- | --- |
| [Identidad, autenticación, sesiones y control de acceso](identidad-autenticacion.md) | HU19, EC08 y EC06: registro, KYC, JWT, sesión nativa y web, administración de usuarios, permisos y auditoría |
| [Inicio de sesión biométrico](inicio-sesion-biometrico.md) | HU02: biometría Android, Keystore, refresh y fallback |

## Perfilamiento e integraciones

| Documento | Contenido |
| --- | --- |
| [Enriquecimiento del perfil](enriquecimiento.md) | HU10: consentimiento, Open Finance, Open Data y señales consolidadas |
| [Perfil de riesgo y pricing](perfil-de-riesgo.md) | HU11: puntaje, dictamen, extraprima y reglas |
| [Socios de distribución](socios-distribucion.md) | HU24: alta, tenant lógico, credenciales, OAuth y scopes |

## Pólizas

| Documento | Contenido |
| --- | --- |
| [Billetera digital de pólizas](billetera-digital.md) | HU07: billetera, estados, certificado con QR y enlace temporal para compartir |

## Clientes, ejecución y evidencias

- [Cliente web](../web/README.md): pantallas, ejecución, configuración y pruebas.
- [Aplicación Android](../android/README.md): construcción y ejecución de la app.
- [Backend y proveedores KYC locales](../README.md#backend-en-local).
- [Infraestructura](../infra/README.md).
- [Evidencias de HU02](evidencias/hu02/README.md).

Los contratos ejecutables de la API están disponibles en `/docs` y `/openapi.json`
al iniciar el backend; las rutas de este directorio describen su uso y contexto.

## Estructura de los documentos

Para nuevos documentos de funcionalidad, mantener esta organización y adaptar las
secciones complementarias según corresponda:

1. **Qué hace:** propósito, alcance e historia relacionada.
2. **Flujo:** pasos desde la entrada hasta el resultado.
3. **Endpoints:** método, ruta, permisos, entrada y respuesta; ejemplos cuando ayuden.
4. **Seguridad o reglas:** validaciones y decisiones específicas del módulo.
5. **Configuración y cómo probar en local:** dependencias, variables y comandos.
6. **Pruebas:** escenarios cubiertos y ubicación de las suites.
7. **Pendientes conocidos:** limitaciones vigentes, sin presentar simuladores como integraciones reales.

En documentos transversales, indicar si reutilizan endpoints y si no exponen una
API propia. Enlazar los contratos compartidos para evitar descripciones contradictorias.
