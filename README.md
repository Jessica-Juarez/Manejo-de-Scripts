# Tareas claras

Aplicación web sencilla para registrar y eliminar tareas. Está hecha con Python y la biblioteca estándar, y se empaqueta con Docker.

## Ejecutar y probar localmente

Requisitos: Python 3.12 o posterior.

```bash
python -m unittest discover -s tests -v
python app.py
```

Abre <http://localhost:8080>. La aplicación también publica `/healthz` para comprobar su estado y `/metrics` para consultar métricas JSON.

## Ejecutar con Docker

Requisitos: Docker Engine y el complemento Docker Compose v2.

```bash
bash scripts/setup-release.sh
docker compose up -d --build
```

Comprueba <http://localhost:8080/healthz>. Para detenerla, ejecuta `docker compose down`.

## Pipeline y despliegue

`.github/workflows/pipeline.yml` ejecuta las pruebas y verifica la imagen en cada pull request y cambio a `main`. Los cambios a `main` también se despliegan por SSH al entorno GitHub `production`.

Para activar el despliegue:

1. Crea un repositorio GitHub y configura en **Settings → Environments** un entorno llamado `production`.
2. Añade estos *secrets* al entorno: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` (clave privada) y `DEPLOY_KNOWN_HOSTS` (clave de host SSH verificada por un canal confiable).
3. Añade la variable `DEPLOY_PATH`, por ejemplo `/opt/tareas-claras`.
4. Prepara un servidor Linux con Docker Engine, Docker Compose v2 y `curl`. Permite SSH desde GitHub Actions y el acceso al puerto de la aplicación (8080 por defecto).
5. Configura el remoto del repositorio y sube la rama `main`. Los comandos y los detalles están en [`docs/entrega.md`](docs/entrega.md).

La carpeta actual ya es un repositorio Git local en la rama `main`; no tiene remoto configurado ni se ha creado un commit. Hace falta enlazarla al repositorio GitHub que vayas a usar.

## Archivos de entrega

- [`docs/entrega.md`](docs/entrega.md): caso de estudio, pipeline, entorno, niveles de servicio, métricas y configuración.
- [`.github/workflows/pipeline.yml`](.github/workflows/pipeline.yml): pruebas, validación de la imagen y despliegue continuo.
- [`scripts/setup-release.sh`](scripts/setup-release.sh): preparación y validación del entorno de liberación.
- [`scripts/deploy.sh`](scripts/deploy.sh): generación y comprobación del despliegue.
- [`tests/test_app.py`](tests/test_app.py): pruebas automatizadas.

> La lista de tareas se guarda en memoria: si el contenedor se reinicia o se vuelve a desplegar, los datos se pierden. Es una limitación deliberada de este proyecto de demostración.
