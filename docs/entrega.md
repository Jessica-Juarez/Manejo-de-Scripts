# Caso de estudio: liberación y despliegue de Tareas claras

## 1. Descripción y alcance

Tareas claras es una aplicación web pequeña para que una persona o un equipo reduzca una lista de trabajo pendiente. Permite consultar, agregar y eliminar tareas. Su API ofrece comprobaciones de salud y métricas para que tanto el pipeline como un monitor externo puedan observar el servicio.

Este caso es una demostración académica de CI/CD. La aplicación no tiene autenticación ni almacenamiento persistente; no debe usarse para datos sensibles o cargas de producción. Las tareas se mantienen en memoria y se pierden cuando el proceso se reinicia.

## 2. Justificación del flujo de trabajo

El pipeline está implementado en `.github/workflows/pipeline.yml` con GitHub Actions:

1. **Pull request o push a `main`:** prepara Python 3.12 y ejecuta las pruebas unitarias. Los cambios que no pasan las pruebas no avanzan.
2. **Validación de liberación:** prepara el entorno Docker, construye la imagen y ejecuta el contenedor. Consulta `/healthz` antes de considerar válida la imagen. Así se comprueba el artefacto ejecutable, no solo el código fuente.
3. **Push a `main`:** después de la validación, el trabajo `deploy` usa el entorno protegido de GitHub `production`, copia el proyecto por SSH y ejecuta los scripts de preparación y despliegue en el servidor.

Separar pruebas, validación y despliegue permite detectar fallos antes de modificar el entorno publicado. El despliegue solo ocurre desde `main`; los pull requests no acceden a credenciales de producción. El identificador de la ejecución y el commit quedan registrados en GitHub Actions. Se puede exigir aprobación manual antes de desplegar configurando revisores requeridos en el entorno `production`.

## 3. Entorno requerido

### Integración y liberación

- Repositorio GitHub con la rama `main`.
- GitHub Actions habilitado.
- Runner `ubuntu-latest` administrado por GitHub.
- Python 3.12 y Docker Compose v2 disponibles en el runner.
- Entorno de GitHub Actions llamado `production`, con los secretos y variable indicados en la sección 6.

### Servidor de despliegue

- Linux x86_64, recomendado Ubuntu Server 22.04 o posterior.
- Docker Engine y complemento Docker Compose v2, ejecutables por el usuario de despliegue sin intervención interactiva.
- `curl` y acceso a Internet para descargar la imagen base al construir.
- Acceso SSH desde el runner y un puerto TCP disponible (8080 por defecto).
- Directorio de despliegue, por ejemplo `/opt/tareas-claras`, con permisos de escritura para el usuario SSH.

El servidor construye la imagen al ejecutar `docker compose up -d --build`; no se necesita un registro de imágenes adicional.

## 4. Niveles de servicio acordados (objetivos de demostración)

Estos objetivos son un acuerdo de ejemplo para una aplicación académica pequeña; no constituyen una garantía contractual. El período de medición es un mes calendario y el mantenimiento anunciado se excluye de la disponibilidad.

| Indicador | Objetivo | Medición |
|---|---:|---|
| Disponibilidad del endpoint de salud | ≥ 99 % mensual | Sondeo externo de `GET /healthz`; éxito cuando responde HTTP 200 con `{"status":"ok"}`. |
| Tiempo de respuesta | 95 % de respuestas ≤ 500 ms | El monitor externo mide cada solicitud HTTP; el endpoint `/metrics` también informa el promedio medido por la aplicación. |
| Tiempo de despliegue | ≤ 10 minutos | Tiempo desde que inicia el trabajo `deploy` hasta que `/healthz` responde correctamente. |
| Recuperación de un despliegue fallido | ≤ 30 minutos | Revertir al commit anterior y volver a ejecutar el pipeline; requiere intervención del responsable. |

El workflow comprueba la salud al desplegar, pero no es un servicio de sondeo continuo. Para reportar los objetivos mensuales de disponibilidad y latencia se debe conectar un monitor externo que consulte `/healthz` y mida las respuestas. `/metrics` es JSON y no implementa por sí solo el protocolo de exposición de Prometheus.

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

El endpoint `GET /healthz` devuelve `{"status":"ok"}` cuando el servidor atiende solicitudes. Docker Compose lo utiliza como comprobación de salud. Para una operación real se recomienda sondear `/healthz` al menos una vez por minuto y generar alertas ante indisponibilidad o errores repetidos. Los contadores son locales al proceso y se reinician al reiniciar el contenedor.

## 6. Parámetros de configuración

### Aplicación y contenedor

| Parámetro | Ubicación | Valor predeterminado | Descripción |
|---|---|---:|---|
| `PORT` | Entorno del contenedor | `8080` | Puerto en el que escucha el servidor Python dentro del contenedor. |
| `APP_PORT` | `.env` leído por Docker Compose | `8080` | Puerto publicado en el servidor; se puede cambiar si ya está ocupado. |
| `APP_PORT` | `scripts/setup-release.sh` | `8080` | El script crea `.env` si falta y valida que el puerto esté entre 1 y 65535. |
| Tamaño máximo del cuerpo JSON | `app.py` | 16384 bytes | Límite para una solicitud de creación de tarea. |
| Longitud máxima del título | `app.py` | 120 caracteres | Títulos vacíos o demasiado largos se rechazan con HTTP 400. |

`HOST` puede cambiarse para ejecuciones directas de `app.py`; por defecto escucha en `0.0.0.0` dentro del contenedor.

### GitHub Actions y conexión de despliegue

En **Settings → Environments → production**:

| Tipo | Nombre | Contenido |
|---|---|---|
| Secret | `DEPLOY_HOST` | Nombre DNS o dirección del servidor. |
| Secret | `DEPLOY_USER` | Usuario SSH que ejecutará Docker. |
| Secret | `DEPLOY_SSH_KEY` | Clave privada de despliegue, sin contraseña interactiva. |
| Secret | `DEPLOY_KNOWN_HOSTS` | Línea de `known_hosts` para ese servidor, verificada con su administrador. |
| Variable | `DEPLOY_PATH` | Ruta absoluta de instalación, por ejemplo `/opt/tareas-claras`. |

No uses una clave de host obtenida sin verificar: compara su huella por un canal independiente antes de guardarla en `DEPLOY_KNOWN_HOSTS`. La acción SSH rechaza hosts que no coincidan con ese valor. Los secretos solo se exponen al trabajo de despliegue vinculado a `production`.

## 7. Scripts y ejecución

| Archivo | Función |
|---|---|
| `.github/workflows/pipeline.yml` | Pipeline de integración, liberación y despliegue continuo. |
| `scripts/setup-release.sh` | Comprueba Docker, Compose y `curl`; crea y valida `.env`. |
| `scripts/deploy.sh` | Construye y levanta el contenedor, espera la comprobación de salud e informa de los logs si falla. |
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

Para enlazar el repositorio local con el repositorio GitHub que hayas creado, sustituye la URL y ejecuta:

```bash
git remote add origin https://github.com/USUARIO/REPOSITORIO.git
git add .
git commit -m "Crear proyecto Tareas claras y pipeline CI/CD"
git push -u origin main
```

La conexión a GitHub y el despliegue real quedan pendientes de la creación del repositorio remoto, la configuración del entorno y las credenciales SSH descritas arriba. No se han inventado credenciales ni se ha publicado ningún código.
