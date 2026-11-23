# ☁️ Despliegue en la nube

Guía paso a paso para publicar el proyecto en internet con servicios **gratuitos**.

| Pieza | Servicio | Notas del plan gratuito |
|---|---|---|
| Base de datos PostgreSQL | **Neon** | 1 GB por proyecto; soporta TimescaleDB |
| API (FastAPI, Docker) | **Render** — Web Service | Se "duerme" tras 15 min sin tráfico y tarda ~1 min en despertar. El ESP32 envía cada minuto, así que la mantiene activa |
| Dashboard (React) | **Render** — Static Site | Siempre activo |

```
ESP32 --HTTPS--> API (Render) --> PostgreSQL (Neon)
                     ^
Navegador --> Dashboard (Render) --HTTPS (consulta la API)
```

> **Seguridad:** la cadena de conexión de Neon (`DATABASE_URL`) contiene la contraseña de la base.
> Solo se guarda en las variables de entorno de Render y en tu terminal. **Nunca** en archivos del repositorio.

---

## 0. Antes de empezar

- El código debe estar en la rama `main` de GitHub (Render despliega desde ahí).
- Docker Desktop abierto (se usa para ejecutar `psql` sin instalarlo).
- Todos los comandos se ejecutan en **Git Bash**, desde la raíz del repositorio.

## 1. Crear la base de datos en Neon

1. Entrar a **neon.com** con la cuenta de GitHub → **New Project**.
2. Nombre: `microclima`. Región: **AWS US West 2 (Oregon)** (la misma región que se usará en Render).
3. En **Connection string**, copiar la cadena completa (empieza con `postgresql://` y termina con `sslmode=require`).
4. Guardarla en la terminal **entre comillas simples** (contiene caracteres especiales):
   ```bash
   export DATABASE_URL='postgresql://usuario:contraseña@ep-xxxx.us-west-2.aws.neon.tech/neondb?sslmode=require'
   ```
   > Esta variable solo existe en esa terminal. Si abres otra, repite el `export`.

## 2. Crear las tablas en Neon

Se usa `psql` desde un contenedor de Docker (no hace falta instalar nada):

```bash
docker run --rm -i postgres:16 psql "$DATABASE_URL" -v ON_ERROR_STOP=1 < db/init/01_esquema.sql
docker run --rm -i postgres:16 psql "$DATABASE_URL" -v ON_ERROR_STOP=1 < db/init/02_modelo.sql
```

✅ Esperado: varios `CREATE TABLE`, `DO`, `CREATE INDEX` y un `INSERT 0 1` (la estación).

> Verificar que `01_esquema.sql` tenga las **coordenadas y altitud reales** de la estación.

## 3. Cargar el histórico ERA5 y crear el token del ESP32

```bash
source .venv/Scripts/activate
python data_science/cargar_bd.py                     # usa DATABASE_URL: carga a Neon
cd api
python -m scripts.crear_token QRO-CENTRO-01          # token NUEVO para la nube
cd ..
```

✅ `cargar_bd.py` debe mostrar **26 304 registros** y **288 combinaciones mes-hora**.
📋 Guardar el token en un lugar seguro: se usa en el paso 6.

### (Opcional) Copiar las lecturas reales que ya tienes en local

Así el dashboard arranca con los días que ya mediste:

```bash
docker exec microclima_db psql -U microclima_admin -d microclima_db \
  -c "\copy (SELECT estacion_id, ts, temperatura_dht, temperatura_bmp, humedad, presion_hpa, iluminancia_lux, recibida_en FROM lecturas ORDER BY ts) TO STDOUT WITH CSV" > lecturas_locales.csv

docker run --rm -i postgres:16 psql "$DATABASE_URL" \
  -c "\copy lecturas (estacion_id, ts, temperatura_dht, temperatura_bmp, humedad, presion_hpa, iluminancia_lux, recibida_en) FROM STDIN WITH CSV" < lecturas_locales.csv
```

> `lecturas_locales.csv` está cubierto por `*.csv` en `.gitignore`. Bórralo después.

## 4. Desplegar en Render (Blueprint)

1. Entrar a **render.com** con la cuenta de GitHub.
2. **New → Blueprint** → conectar el repositorio. Si el repositorio es de una organización,
   dar acceso a la app de Render en GitHub para esa organización.
3. Render lee `render.yaml` y muestra dos servicios: `microclima-api` y `microclima-dashboard`.
   Completar las variables:

   | Variable | Valor (primera vez) |
   |---|---|
   | `DATABASE_URL` | la cadena de Neon |
   | `ORIGENES_CORS` | `["https://microclima-dashboard.onrender.com"]` |
   | `VITE_API_URL` | `https://microclima-api.onrender.com` |

4. **Apply**. La primera construcción tarda algunos minutos.
5. **Importante:** si Render asignó direcciones distintas (ej. `microclima-api-x1y2.onrender.com`),
   corregir las dos variables con las direcciones reales y volver a desplegar:
   - En `microclima-api` → **Environment** → `ORIGENES_CORS`.
   - En `microclima-dashboard` → **Environment** → `VITE_API_URL` → **Manual Deploy → Deploy latest commit**
     (la página lee esta variable al compilar).

## 5. Verificar

- `https://<api>.onrender.com/salud` → `{"estado":"ok","base_de_datos":"ok"}`
- `https://<api>.onrender.com/docs` → documentación interactiva.
- En Render → `microclima-api` → **Logs** → aparece `Modelo sincronizado: {'QRO-CENTRO-01': ...}`.
- `https://<dashboard>.onrender.com` → el dashboard con los datos.

## 6. Conectar el ESP32 a la nube

En `iot/firmware/include/secretos.h`:

```cpp
constexpr char API_URL_BASE[] = "https://<api>.onrender.com";   // sin barra al final
constexpr char API_TOKEN[] = "token creado en el paso 3";
```

**Upload** y abrir el Monitor Serial. La conexión usa **HTTPS con verificación de certificado**
(`include/certificados.h`).

✅ Esperado en ~1 minuto: `registrada (201)`. Si la API estaba dormida, las primeras lecturas
pueden fallar por tiempo de espera: quedan en la cola y se envían solas al despertar.

---

## Solución de problemas

| Síntoma | Causa probable |
|---|---|
| El dashboard dice "No se pudo actualizar: Failed to fetch" | `VITE_API_URL` incorrecta, o `ORIGENES_CORS` no incluye la dirección exacta del dashboard (con `https://`, sin barra final) |
| El dashboard tarda ~1 min en cargar | La API estaba dormida (plan gratuito). Normal si el ESP32 está apagado |
| `/salud` da error 500 | `DATABASE_URL` incorrecta: revisar en Render → Environment |
| El ESP32 muestra `token invalido (401/403)` | El token del paso 3 no está en `secretos.h` (el token local no sirve en la nube) |
| El ESP32 muestra `connection refused` o errores de conexión | Falta `https://` en `API_URL_BASE` o la hora no está sincronizada (HTTPS requiere hora correcta) |
| La brecha térmica aparece vacía | El modelo aún no se sincronizó: revisar los Logs de la API |
