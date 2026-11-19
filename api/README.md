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

## Seguridad

- Cada estación tiene un **token aleatorio de 256 bits**; en la base solo se guarda su **hash SHA-256**.
- Un token solo puede escribir datos de su propia estación.
- Validación doble: Pydantic en la API y restricciones `CHECK` en PostgreSQL.
- Consultas SQL parametrizadas (protección contra inyección SQL).
- CORS restringido a los orígenes configurados; el contenedor corre sin privilegios de root.

## Desarrollo local

```bash
cd api
pip install -r requirements-dev.txt
uvicorn app.main:app --reload        # API en http://localhost:8000
python -m pytest                     # pruebas (requiere la base levantada)
python -m scripts.crear_token QRO-CENTRO-01   # genera el token del ESP32
```
