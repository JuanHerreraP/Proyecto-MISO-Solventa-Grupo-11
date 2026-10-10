# Solventa — Proyecto Final MISO, Grupo 11

Plataforma de seguros embebidos con canal web, app Android y backend en la nube.

Integrantes: Ana María Solano, Harold Virgüez, Juan Esteban Herrera, Fernando Parra.

## Estructura del repositorio

| Carpeta | Contenido | Stack |
|---|---|---|
| `backend/` | Servicios de dominio y adaptadores | Python 3.12, FastAPI, Pytest |
| `web/` | Portal web | React, TypeScript, Vite, Vitest |
| `android/` | App móvil nativa | Kotlin, Jetpack Compose, JUnit |
| `infra/` | Infraestructura y despliegue en AWS | ECS Fargate, Aurora PostgreSQL, ElastiCache Redis, SNS/SQS |
| `docs/` | Documentación técnica que acompaña el código | Markdown |

La documentación de arquitectura y las entregas semanales están en la [wiki](https://github.com/JuanHerreraP/Proyecto-MISO-Solventa-Grupo-11/wiki). El backlog está en [Jira (BPM)](https://proyecto-miso-grupo-11.atlassian.net/jira/software/projects/BPM/boards/3/backlog).

## Cómo trabajar

El flujo de ramas, la convención de commits y el versionamiento están en [CONTRIBUTING.md](CONTRIBUTING.md). Nadie hace push directo a `main`.

## Backend en local

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
uvicorn app.main:app --reload
```

La documentación OpenAPI queda en `http://localhost:8000/docs`.

# KYC en local

Se incorpora validación de identidad mediante un proveedor KYC desacoplado. Para desarrollo y pruebas locales se incluyen tres servicios simulados:

| Proveedor | Servicio               | Puerto |
| --------- | ---------------------- | ------ |
| A         | `mocks.kyc.provider_a` | `8001` |
| B         | `mocks.kyc.provider_b` | `8002` |
| C         | `mocks.kyc.provider_c` | `8003` |

El backend selecciona el proveedor mediante la variable de entorno `KYC_PROVIDER`.

Por defecto se utiliza el proveedor `A`.

### Ejecución con proveedor A

En una terminal, desde `backend/`:

```bash
source .venv/bin/activate
uvicorn mocks.kyc.provider_a:app --reload --port 8001
```

En otra terminal:

```bash
source .venv/bin/activate
KYC_PROVIDER=A uvicorn app.main:app --reload --port 8000
```

### Ejecución con proveedor B

```bash
uvicorn mocks.kyc.provider_b:app --reload --port 8002
```

Y ejecutar el backend con:

```bash
KYC_PROVIDER=B uvicorn app.main:app --reload --port 8000
```

### Ejecución con proveedor C

```bash
uvicorn mocks.kyc.provider_c:app --reload --port 8003
```

Y ejecutar el backend con:

```bash
KYC_PROVIDER=C uvicorn app.main:app --reload --port 8000
```

Para probar los tres proveedores simultáneamente se pueden levantar los mocks en terminales independientes:

```bash
uvicorn mocks.kyc.provider_a:app --reload --port 8001
uvicorn mocks.kyc.provider_b:app --reload --port 8002
uvicorn mocks.kyc.provider_c:app --reload --port 8003
```

El proveedor utilizado por Solventa continuará siendo el indicado en `KYC_PROVIDER`.

Los servicios simulados exponen endpoints de salud en:

- `http://localhost:8001/health`
- `http://localhost:8002/health`
- `http://localhost:8003/health`

Las URL pueden sobrescribirse mediante variables de entorno:

| Variable             | Valor local por defecto |
| -------------------- | ----------------------- |
| `KYC_PROVIDER`       | `A`                     |
| `KYC_PROVIDER_A_URL` | `http://127.0.0.1:8001` |
| `KYC_PROVIDER_B_URL` | `http://127.0.0.1:8002` |
| `KYC_PROVIDER_C_URL` | `http://127.0.0.1:8003` |

Esta separación permite sustituir el proveedor KYC sin modificar el servicio consumidor, de acuerdo con el experimento arquitectónico EC06.

## Funcionalidades

- [Registro, onboarding seguro y autenticación basada en tokens (HU19)](docs/identidad-autenticacion.md)
- [Enriquecimiento del perfil con Open Finance y Open Data (HU10)](docs/enriquecimiento.md)
- [Perfil de riesgo individualizado y pricing (HU11)](docs/perfil-de-riesgo.md)

## Integración continua

`.github/workflows/ci.yml` corre en cada pull request y en cada push a `main`. Ejecuta lint y pruebas con cobertura del backend, y detecta si existen los proyectos web y Android y solo entonces corre sus trabajos.
