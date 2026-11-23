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

`.github/workflows/pipeline.yml` ejecuta las pruebas y verifica la imagen en cada pull request y cambio a `main`. Después de validar un cambio a `main`, solicita a Render el despliegue del commit probado.

Para activar el despliegue:

1. En [Render](https://dashboard.render.com/), crea un **Web Service**, conecta este repositorio y elige la rama `main`, lenguaje **Docker** y plan **Free**. Configura `/healthz` como Health Check Path.
2. Desactiva **Auto-Deploy** en la configuración del servicio para que los cambios posteriores se desplieguen únicamente después de las pruebas de GitHub Actions. La creación inicial del servicio puede iniciar un primer despliegue.
3. Copia el **Deploy Hook** desde **Settings** del servicio. Es una URL secreta: no la publiques ni la compartas por chat.
4. En GitHub, entra a **Settings → Environments → production → Environment secrets** y crea `RENDER_DEPLOY_HOOK_URL` con esa URL.
5. Sube estos cambios a `main` y comprueba la ejecución en GitHub Actions y luego el estado del despliegue en Render. Una respuesta exitosa al hook solo significa que Render aceptó la solicitud; no confirma que la aplicación ya se haya publicado.

En el plan gratuito, Render detiene la aplicación tras 15 minutos sin tráfico y puede tardar aproximadamente un minuto en reactivarla. Al detenerse se pierden las tareas en memoria; revisa los [límites del plan gratuito](https://render.com/docs/free).

## Archivos de entrega

- [`docs/entrega.md`](docs/entrega.md): caso de estudio, pipeline, entorno, niveles de servicio, métricas y configuración.
- [`.github/workflows/pipeline.yml`](.github/workflows/pipeline.yml): pruebas, validación de la imagen y despliegue continuo.
- [`scripts/setup-release.sh`](scripts/setup-release.sh): preparación y validación del entorno de liberación.
- [`scripts/deploy-render.sh`](scripts/deploy-render.sh): solicita el despliegue en Render del commit validado.
- [`scripts/deploy.sh`](scripts/deploy.sh): despliegue y comprobación local con Docker Compose.
- [`tests/test_app.py`](tests/test_app.py): pruebas automatizadas.

> La lista de tareas se guarda en memoria: si el contenedor se reinicia o se vuelve a desplegar, los datos se pierden. Es una limitación deliberada de este proyecto de demostración.
