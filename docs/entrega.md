# Caso de estudio: liberación y despliegue de Tareas claras

## 1. Descripción y alcance

Tareas claras es una aplicación web pequeña para que una persona o un equipo reduzca una lista de trabajo pendiente. Permite consultar, agregar y eliminar tareas. Su API ofrece comprobaciones de salud y métricas para que tanto el pipeline como un monitor externo puedan observar el servicio.

Este caso es una demostración académica de CI/CD. La aplicación no tiene autenticación ni almacenamiento persistente; no debe usarse para datos sensibles o cargas de producción. Las tareas se mantienen en memoria y se pierden cuando el proceso se reinicia.

## 2. Justificación del flujo de trabajo

El pipeline está implementado en `.github/workflows/pipeline.yml` con GitHub Actions:

1. **Pull request o push a `main`:** prepara Python 3.12 y ejecuta las pruebas unitarias. Los cambios que no pasan las pruebas no avanzan.
2. **Validación de liberación:** prepara el entorno Docker, construye la imagen y ejecuta el contenedor. Consulta `/healthz` antes de considerar válida la imagen. Así se comprueba el artefacto ejecutable, no solo el código fuente.
3. **Push a `main`:** después de la validación, el trabajo `deploy` usa el entorno GitHub `production` y solicita por medio del deploy hook de Render que se construya y publique el commit exacto que pasó las pruebas.

Separar pruebas, validación y despliegue permite detectar fallos antes de solicitar la publicación. El hook solo se ejecuta desde `main`; los pull requests no acceden al secreto. El identificador de la ejecución y el commit quedan registrados en GitHub Actions. Se puede exigir aprobación manual antes de desplegar configurando revisores requeridos en el entorno `production`, si la cuenta y visibilidad del repositorio lo permiten. Desactiva Auto-Deploy en Render para que no publique directamente los cambios de GitHub sin esperar las pruebas.

El hook confirma que Render inició o puso en espera el despliegue, no que haya terminado correctamente. El resultado final debe comprobarse en el panel de Render y consultando `/healthz`. Render construye una imagen nueva desde el mismo commit: no reutiliza la imagen construida en el runner.

## 3. Entorno requerido

### Integración y liberación

- Repositorio GitHub con la rama `main`.
- GitHub Actions habilitado.
- Runner `ubuntu-latest` administrado por GitHub.
- Python 3.12 y Docker Compose v2 disponibles en el runner.
- Entorno de GitHub Actions llamado `production`, con el secreto indicado en la sección 6.

### Plataforma de despliegue

- Cuenta de Render y servicio web conectado al repositorio GitHub y a la rama `main`.
- Runtime Docker con el `Dockerfile` ubicado en la raíz y ruta de salud `/healthz`.
- Auto-Deploy desactivado; GitHub Actions solicita cada despliegue mediante el hook.
- Una instancia Free es suficiente para la demostración. Render gestiona el servidor y construye la imagen; no es necesario configurar SSH.

En el plan Free, el servicio se detiene después de 15 minutos sin tráfico y puede tardar aproximadamente un minuto en reactivarse. Las tareas en memoria se pierden al detenerse o reiniciarse. Consulta [las condiciones y límites vigentes de Render](https://render.com/docs/free); pueden existir cargos por uso excedente si hay un método de pago configurado.

## 4. Niveles de servicio acordados (objetivos de demostración)

Estos objetivos son un acuerdo de ejemplo para una aplicación académica pequeña; no constituyen una garantía contractual. El período de medición es un mes calendario y el mantenimiento anunciado se excluye de la disponibilidad.

| Indicador | Objetivo | Medición |
|---|---:|---|
| Disponibilidad del endpoint de salud | ≥ 99 % mensual | Sondeo externo de `GET /healthz`; éxito cuando responde HTTP 200 con `{"status":"ok"}`. |
| Tiempo de respuesta | 95 % de respuestas ≤ 500 ms | El monitor externo mide cada solicitud HTTP; el endpoint `/metrics` también informa el promedio medido por la aplicación. |
| Tiempo de despliegue | ≤ 10 minutos | Tiempo desde que inicia el trabajo `deploy` hasta que `/healthz` responde correctamente. |
| Recuperación de un despliegue fallido | ≤ 30 minutos | Revertir al commit anterior y volver a ejecutar el pipeline; requiere intervención del responsable. |

Estos objetivos son aspiracionales y no están garantizados por el plan gratuito: sus suspensiones por inactividad y tiempos de arranque pueden impedir cumplirlos. El workflow comprueba la salud de la imagen en el runner antes del despliegue, pero no comprueba el resultado final en Render ni es un servicio de sondeo continuo. Para medir los objetivos mensuales se debe conectar un monitor externo que consulte `/healthz` y mida las respuestas. `/metrics` es JSON y no implementa por sí solo el protocolo de exposición de Prometheus.

## 5. Métricas para el monitoreo

`GET /metrics` devuelve un documento JSON actualizado desde que arrancó el proceso:

| Métrica | Uso |
|---|---|
| `uptime_seconds` | Detectar reinicios o procesos con poco tiempo en servicio. |
| `requests_total` | Ver el volumen acumulado de solicitudes. |
| `requests_by_route` | Entender qué rutas reciben tráfico; las rutas de tareas se agrupan como `/api/tasks/{id}`. |
| `responses_by_status` | Observar respuestas exitosas y errores HTTP. |
| `average_response_time_ms` | Detectar cambios generales de latencia; usar un monitor externo para percentiles. |
| `tasks_total` | Observar cuántas tareas contiene la instancia en memoria. |

El endpoint `GET /healthz` devuelve `{"status":"ok"}` cuando el servidor atiende solicitudes. Docker Compose y Render pueden utilizarlo como comprobación de salud. Para una operación real se recomienda sondear `/healthz` al menos una vez por minuto y generar alertas ante indisponibilidad o errores repetidos. Los contadores son locales al proceso y se reinician al reiniciar el contenedor.

## 6. Parámetros de configuración

### Aplicación y contenedor

| Parámetro | Ubicación | Valor predeterminado | Descripción |
|---|---|---:|---|
| `PORT` | Entorno del contenedor | `8080` | Puerto en el que escucha el servidor Python dentro del contenedor. |
| `APP_PORT` | `.env` leído por Docker Compose | `8080` | Puerto publicado en la máquina local; se puede cambiar si ya está ocupado. |
| `APP_PORT` | `scripts/setup-release.sh` | `8080` | El script crea `.env` si falta y valida que el puerto esté entre 1 y 65535. |
| Tamaño máximo del cuerpo JSON | `app.py` | 16384 bytes | Límite para una solicitud de creación de tarea. |
| Longitud máxima del título | `app.py` | 120 caracteres | Títulos vacíos o demasiado largos se rechazan con HTTP 400. |

`HOST` puede cambiarse para ejecuciones directas de `app.py`; por defecto escucha en `0.0.0.0` dentro del contenedor.

### GitHub Actions y conexión a Render

En **Settings → Environments → production**:

| Tipo | Nombre | Contenido |
|---|---|---|
| Secret | `RENDER_DEPLOY_HOOK_URL` | URL secreta del Deploy Hook que Render muestra en la configuración del servicio. |

El hook es una credencial: no lo subas al repositorio ni lo compartas por chat. Si se filtra, regenera el hook en Render y actualiza el secreto en GitHub. El script envía el SHA validado como parámetro `ref`, de acuerdo con la [documentación de Render](https://render.com/docs/deploy-hooks).

## 7. Scripts y ejecución

| Archivo | Función |
|---|---|
| `.github/workflows/pipeline.yml` | Pipeline de integración, liberación y despliegue continuo. |
| `scripts/setup-release.sh` | Comprueba Docker, Compose y `curl`; crea y valida `.env`. |
| `scripts/deploy-render.sh` | Solicita a Render el despliegue del commit validado y comprueba que la solicitud sea aceptada. |
| `scripts/deploy.sh` | Construye y levanta el contenedor localmente, espera la comprobación de salud e informa de los logs si falla. |
| `tests/test_app.py` | Prueba la interfaz, API de tareas, validación, salud y métricas. |
| `compose.yaml` y `Dockerfile` | Definen el servicio y la imagen desplegable. |

Prueba local:

```bash
python -m unittest discover -s tests -v
bash scripts/setup-release.sh
bash scripts/deploy.sh
curl http://localhost:8080/healthz
curl http://localhost:8080/metrics
```

### Activación de Render

1. En [Render](https://dashboard.render.com/), crea un **Web Service** y conecta el repositorio GitHub, rama `main`. Elige **Docker** y, si está disponible, el plan **Free**.
2. En la configuración del servicio establece **Health Check Path** a `/healthz` y desactiva **Auto-Deploy**. Render puede iniciar un despliegue inicial al crear el servicio, antes de que el hook quede configurado.
3. Copia el **Deploy Hook** desde **Settings** del servicio y guárdalo como secreto `RENDER_DEPLOY_HOOK_URL` en el entorno `production` de GitHub.
4. Sube los cambios del proyecto. Comprueba en **Actions** que las pruebas pasen y que la solicitud a Render sea aceptada.
5. En Render, verifica que el despliegue termine correctamente y abre la URL pública con `/healthz` y `/metrics`.

El despliegue real queda pendiente de crear y configurar el servicio Render y el secreto de GitHub. No se han inventado credenciales.
