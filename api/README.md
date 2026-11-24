# API — Monitoreo Microclimático

API REST construida con **FastAPI** que recibe las lecturas del ESP32, las valida y las compara con la climatología histórica.

Documentación interactiva (con la API corriendo): **http://localhost:8000/docs**

## Endpoints

| Método | Ruta | Autenticación | Descripción |
|---|---|---|---|
| `GET` | `/salud` | — | Verifica que la API y la base respondan |
| `GET` | `/api/v1/estaciones` | — | Lista las estaciones |
| `POST` | `/api/v1/lecturas` | Token | Registra una lectura del sensor |
| `GET` | `/api/v1/estaciones/{codigo}/lecturas?horas=24` | — | Lecturas recientes |
| `GET` | `/api/v1/estaciones/{codigo}/comparacion?horas=24` | — | Lecturas vs. climatología (anomalía) |
| `GET` | `/api/v1/estaciones/{codigo}/brecha?horas=24` | — | Brecha térmica hora por hora: sensor vs. modelo meteorológico |
| `GET` | `/api/v1/estaciones/{codigo}/brecha/minutos?horas=3` | — | Brecha minuto a minuto (modelo y normal interpolados linealmente entre horas) |
| `GET` | `/api/v1/estaciones/{codigo}/estado` | — | Estado remoto: `midiendo`, `en_espera`, `desconectado` o `desconocido` |
| `POST` | `/api/v1/admin/login` | — | Inicia sesión de administrador (devuelve un token de sesión de 8 h) |
| `GET` | `/api/v1/admin/sesion` | Admin | Verifica la sesión actual |
| `POST` | `/api/v1/admin/logout` | Admin | Cierra la sesión |
| `POST` | `/api/v1/estaciones/{codigo}/comando` | Admin | Envía `{"accion":"activar"}` o `{"accion":"detener"}` por MQTT |
| `GET` | `/api/v1/estaciones/{codigo}/comandos` | Admin | Historial de órdenes (auditoría) |

> **Ventana anclada:** las consultas devuelven las N horas que **terminan en la última lectura**
> de la estación (no en "ahora"). Si la estación está detenida, el sitio muestra sus datos más
> recientes en lugar de quedar vacío.

## Contrato de la lectura (lo que envía el ESP32)

```http
POST /api/v1/lecturas
Authorization: Bearer <token de la estación>
Content-Type: application/json
```
```json
{
  "estacion": "QRO-CENTRO-01",
  "ts": "2026-11-19T14:30:00-06:00",
  "temperatura_dht": 24.0,
  "temperatura_bmp": 23.6,
  "humedad": 41.0,
  "presion_hpa": 812.4,
  "iluminancia_lux": 35200.0
}
```

| Respuesta | Significado |
|---|---|
| `201` | Lectura registrada |
| `401` | Token ausente o inválido |
| `403` | El token no pertenece a esa estación |
| `409` | Ya existe una lectura en ese instante |
| `422` | Datos inválidos (fuera de rango, sin zona horaria, en el futuro o campos desconocidos) |

## Dos comparaciones distintas

| Endpoint | Compara contra | Responde a |
|---|---|---|
| `/comparacion` | **Climatología**: promedio ERA5-Land 2023–2025 para ese mes y hora | ¿Hoy está más caliente **de lo normal** para esta época? |
| `/brecha` | **Modelo meteorológico** (Open-Meteo) en la **misma hora** | ¿Cuánto más caliente está **la calle** que la región **ahora mismo**? → isla de calor |

### Cómo se calcula la brecha (`/brecha`)

- **Temperatura y humedad:** promedio de las lecturas de ±30 min alrededor de cada hora en punto,
  porque el modelo entrega valores instantáneos. El modelo se pide **ajustado a la altitud de la
  estación**, así la brecha no incluye el efecto de la diferencia de altura.
- **Presión:** la presión de la estación se **reduce al nivel del mar** (fórmula barométrica) para
  compararla con la presión a nivel del mar del modelo. Sirve como control de calibración del BME280.
- **Radiación:** el BH1750 mide luz en **lux**, no radiación. Se **estima** con lux ÷ 120 (válido solo
  con sol directo) y se compara con la hora anterior, porque el modelo entrega el promedio horario.

El servicio `sincronizador` descarga el modelo cada 30 minutos y lo guarda en la tabla `modelo_horario`.

## Seguridad

- Cada estación tiene un **token aleatorio de 256 bits**; en la base solo se guarda su **hash SHA-256**.
- Un token solo puede escribir datos de su propia estación.
- Validación doble: Pydantic en la API y restricciones `CHECK` en PostgreSQL.
- Consultas SQL parametrizadas (protección contra inyección SQL).
- CORS restringido a los orígenes configurados; el contenedor corre sin privilegios de root.
- Contraseñas de administrador con **scrypt** (sal aleatoria); las sesiones son tokens opacos y en
  la base solo se guarda su hash. Expiran a las 8 h y se pueden cerrar.
- **Límite de intentos:** 5 contraseñas incorrectas en 15 min por IP → `429`. El mensaje de error
  es el mismo si el usuario no existe (no revela qué usuarios hay).
- Cada orden activar / detener queda registrada (quién y cuándo) en la tabla `comandos`.
- MQTT sobre **TLS** (puerto 8883) con una credencial distinta para la API y para el ESP32.

### Control remoto (MQTT)

| Tema | Quién publica | Contenido (retenido) |
|---|---|---|
| `microclima/<codigo>/comando` | API | `{"accion":"activar"\|"detener","ts":...}` |
| `microclima/<codigo>/estado` | ESP32 | `{"estado":"midiendo"\|"en_espera","ts":...}`; si se desconecta, el broker publica `{"estado":"desconectado"}` (LWT) |

Las lecturas siguen llegando por HTTPS; MQTT solo transporta órdenes y estado.
Crear un administrador: `python -m scripts.crear_admin <usuario>` (pide la contraseña sin mostrarla).

## Desarrollo local

```bash
cd api
pip install -r requirements-dev.txt
uvicorn app.main:app --reload        # API en http://localhost:8000
python -m pytest                     # pruebas (requiere la base levantada)
python -m scripts.crear_token QRO-CENTRO-01   # genera el token del ESP32
python -m scripts.sincronizar_modelo          # descarga el modelo una vez (manual)
```
