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

## Funcionalidades

- [Perfil de riesgo individualizado y pricing (HU11)](docs/perfil-de-riesgo.md)

## Integración continua

`.github/workflows/ci.yml` corre en cada pull request y en cada push a `main`. Ejecuta lint y pruebas con cobertura del backend, y activa los trabajos de web y Android cuando esas carpetas tengan proyecto.
