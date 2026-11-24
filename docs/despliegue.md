# ☁️ Despliegue en la nube

Guía paso a paso para publicar el proyecto en internet con servicios **gratuitos**.

| Pieza | Servicio | Notas del plan gratuito |
|---|---|---|
| Base de datos PostgreSQL | **Neon** | 1 GB por proyecto; soporta TimescaleDB |
| API (FastAPI, Docker) | **Render** — Web Service | Se "duerme" tras 15 min sin tráfico y tarda ~1 min en despertar. El ESP32 envía cada minuto, así que la mantiene activa |
| Dashboard (React) | **Render** — Static Site | Siempre activo |
| Broker MQTT (activar / detener) | **EMQX Cloud** — Serverless | 1 millón de minutos de sesión y 1 GB/mes, sin tarjeta |

```
ESP32 --HTTPS (lecturas)--> API (Render) --> PostgreSQL (Neon)
  ^                           |
  +---- MQTT (órdenes) ---   EMQX Cloud <--- (la API publica "activar"/"detener")
                              ^
Navegador --> Dashboard (Render) --HTTPS (consulta la API / panel Admin)
```

> **Seguridad:** la cadena de conexión de Neon (`DATABASE_URL`), las contraseñas de EMQX y la del
> administrador son secretas. Solo se guardan en las variables de entorno de Render, en tu terminal
> y en `secretos.h` (ignorado por Git). **Nunca** en archivos del repositorio ni en el chat.

---

## 0. Antes de empezar

- El código debe estar en la rama `main` de GitHub (Render despliega desde ahí).
- Docker Desktop abierto (se usa para ejecutar `psql` sin instalarlo).
- Todos los comandos se ejecutan en **Git Bash**, desde la raíz del repositorio.

## 1. Crear la base de datos en Neon

1. Entrar a **neon.com** con la cuenta de GitHub → **New Project**.
2. Nombre: `microclima`. Región: **AWS US East 1 (N. Virginia)** (la misma región que la API en Render: `region: virginia` en `render.yaml`).
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
docker run --rm -i postgres:16 psql "$DATABASE_URL" -v ON_ERROR_STOP=1 < db/init/03_admin.sql
```

✅ Esperado: varios `CREATE TABLE`, `DO`, `CREATE INDEX` y un `INSERT 0 1` (la estación).
Los tres archivos se pueden volver a ejecutar sin problema (no borran datos).

> Verificar que `01_esquema.sql` tenga las **coordenadas y altitud reales** de la estación.

## 3. Cargar el histórico ERA5 y crear el token del ESP32

```bash
source .venv/Scripts/activate
python data_science/cargar_bd.py                     # usa DATABASE_URL: carga a Neon
cd api
python -m scripts.crear_token QRO-CENTRO-01          # token NUEVO para la nube
python -m scripts.crear_admin malu                   # usuario del panel Admin (pide la contraseña)
cd ..
```

✅ `cargar_bd.py` debe mostrar **26 304 registros** y **288 combinaciones mes-hora**.
📋 Guardar el token en un lugar seguro: se usa en el paso 6.
🔐 La contraseña del administrador debe tener al menos 10 caracteres. No se muestra al escribirla
(es normal). Si se ejecuta otra vez con el mismo usuario, cambia la contraseña y cierra sus sesiones.

### (Opcional) Copiar las lecturas reales que ya tienes en local

Así el dashboard arranca con los días que ya mediste:

```bash
docker exec microclima_db psql -U microclima_admin -d microclima_db \
  -c "\copy (SELECT estacion_id, ts, temperatura_dht, temperatura_bmp, humedad, presion_hpa, iluminancia_lux, recibida_en FROM lecturas ORDER BY ts) TO STDOUT WITH CSV" > lecturas_locales.csv

docker run --rm -i postgres:16 psql "$DATABASE_URL" \
  -c "\copy lecturas (estacion_id, ts, temperatura_dht, temperatura_bmp, humedad, presion_hpa, iluminancia_lux, recibida_en) FROM STDIN WITH CSV" < lecturas_locales.csv
```

> `lecturas_locales.csv` está cubierto por `*.csv` en `.gitignore`. Bórralo después.

## 3.5 Crear el broker MQTT en EMQX Cloud

> HiveMQ Cloud dejó de permitir clústeres gratuitos nuevos (fin del plan *Serverless*), por eso se usa
> **EMQX Cloud Serverless**: gratis hasta 1 millón de minutos de sesión y 1 GB al mes, sin tarjeta.

1. Entrar a **cloud-intl.emqx.com** → crear cuenta → **New Deployment** → elegir **Serverless**.
   Región: **AWS US East 1 (N. Virginia)** si está disponible. **Spend limit: dejar en 0** (así nunca cobra).
2. En el *deployment* → **Overview**: copiar la **Address** (ej. `abc123.ala.us-east-1.emqxsl.com`).
   El puerto TLS es **8883**. El certificado de EMQX está firmado por **DigiCert Global Root G2**,
   que ya está en `iot/firmware/include/certificados.h`.
3. **Access Control → Authentication** → **Add** → crear **dos** usuarios:
   - `api-microclima` → lo usa la API (Render).
   - `esp32-qro-centro-01` → lo usa el ESP32.

   > Dos credenciales distintas: si una se filtra, se borra solo esa sin afectar a la otra.

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
   | `MQTT_HOST` | la Address de EMQX (sin `mqtts://` ni puerto) |
   | `MQTT_USUARIO` / `MQTT_CONTRASENA` | la credencial `api-microclima` |

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
- `https://<api>.onrender.com/api/v1/estaciones/QRO-CENTRO-01/estado` → `{"estado":"desconectado"...}`
  o `"desconocido"` mientras el ESP32 no se haya conectado nunca al broker.
- `https://<dashboard>.onrender.com/#/admin` → iniciar sesión con el usuario del paso 3.

## 6. Conectar el ESP32 a la nube

En `iot/firmware/include/secretos.h`:

```cpp
constexpr char API_URL_BASE[] = "https://<api>.onrender.com";   // sin barra al final
constexpr char API_TOKEN[] = "token creado en el paso 3";

#define MQTT_HOST "la Address de EMQX"
#define MQTT_PUERTO 8883
#define MQTT_USUARIO "esp32-qro-centro-01"
#define MQTT_CONTRASENA "contraseña de esa credencial"
```

**Upload** y abrir el Monitor Serial. La conexión usa **HTTPS con verificación de certificado**
(`include/certificados.h`).

✅ Esperado en ~1 minuto: `registrada (201)`. Si la API estaba dormida, las primeras lecturas
pueden fallar por tiempo de espera: quedan en la cola y se envían solas al despertar.

Con MQTT configurado, la estación arranca **en espera** (la pantalla dice `En espera`).
En el sitio → **Admin** → **Activar**: en pocos segundos el Monitor Serial muestra
`[CONTROL] Nuevo modo: midiendo` y la pantalla vuelve a rotar las mediciones.
La estación recuerda el último modo aunque se reinicie o se quede sin energía.

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
| Admin → "Activar" responde 503 | Variables `MQTT_*` incorrectas en Render (o se usó la credencial del ESP32) |
| Monitor Serial: `No se pudo conectar (codigo 4)` / `(codigo 5)` | Usuario o contraseña MQTT incorrectos en `secretos.h` |
| Monitor Serial: `No se pudo conectar (codigo -2)` | `MQTT_HOST` mal escrito (sin `https://`, sin puerto) o sin internet |
| Admin → demasiados intentos (429) | 5 contraseñas incorrectas en 15 min: esperar. Es una protección contra ataques |
