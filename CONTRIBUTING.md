# Flujo de trabajo y versionamiento

## Ramas

Se usa desarrollo basado en trunk con ramas cortas.

- `main` es la única rama permanente. Siempre debe compilar y pasar las pruebas.
- Cada cambio va en una rama corta que sale de `main` y vuelve a `main` por pull request.
- Una rama no debería vivir más de dos o tres días.

Nombre de la rama: `<tipo>/BPM-<número>-<descripción-corta>`

| Tipo | Uso | Ejemplo |
|---|---|---|
| `feature` | Historia o subtarea | `feature/BPM-90-endpoint-registro` |
| `fix` | Corrección de un defecto | `fix/BPM-92-expiracion-token` |
| `chore` | Configuración, pipeline, dependencias | `chore/BPM-97-secretos-jwt` |
| `docs` | Solo documentación | `docs/estrategia-de-ramas` |

La clave de Jira en el nombre de la rama enlaza el trabajo con la incidencia.

## Commits

Formato [Conventional Commits](https://www.conventionalcommits.org/es/) con la clave de Jira:

```
feat(identidad): endpoint de registro de usuarios BPM-90
fix(perfilamiento): timeout de Open Finance BPM-127
test(socios): aislamiento entre tenants BPM-150
```

Tipos: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`, `ci`.

## Pull requests

1. Abrir el PR contra `main` usando la plantilla.
2. El pipeline de integración continua debe estar en verde.
3. Se requiere al menos una aprobación de otro integrante.
4. Se fusiona con *squash and merge* para que `main` tenga un commit por cambio.
5. Se borra la rama después de fusionar.

Protección recomendada de `main` (Settings → Branches): exigir PR, una aprobación, checks de CI en verde y prohibir el push directo.

## Definición de terminado

Una historia se da por terminada cuando:

- cumple sus criterios de aceptación en Jira;
- tiene pruebas automatizadas y el pipeline pasa;
- el PR fue revisado y fusionado a `main`;
- quedó desplegada en el ambiente de pruebas;
- la incidencia de Jira está en "Finalizada".

## Versionamiento

Versionamiento semántico (`MAYOR.MENOR.PARCHE`) con etiquetas de Git sobre `main`.

| Momento | Versión |
|---|---|
| Cierre del Sprint 1 | `v0.1.0` |
| Cierre del Sprint 2 | `v0.2.0` |
| Cierre del Sprint 3 | `v0.3.0` |
| Entrega final | `v1.0.0` |

Las correcciones posteriores al cierre de un sprint suben el parche (`v0.1.1`). Cada etiqueta de cierre de sprint lleva un *release* de GitHub con las historias incluidas.

## Ramas anteriores

Las ramas `feature/exp-1`, `feature/exp-2`, `feature/exp-3` y `feature/style-tile` son del Proyecto Final 1. Su código se incorpora por PR a medida que una historia lo necesite; no se fusionan completas.
