# 🧭 Flujo de trabajo diario

Guía rápida con los comandos del proyecto **en el orden en que se ejecutan**.
Todos los comandos se ejecutan en la terminal **Bash** de VS Code, desde la carpeta raíz del repositorio.

> **Idea general**
> - **Docker** = el "servidor" (base de datos + API). Se enciende **una vez** por sesión y queda en segundo plano.
> - **venv** = el Python del proyecto. Se activa **en cada terminal nueva**.
> - **Git** = **actualizar antes** de empezar y **guardar (commit/push) antes** de terminar.

---

## ☀️ Al empezar el día

### 1. Abrir Docker Desktop
Abrirlo **antes** que VS Code y esperar a que la ballena 🐳 deje de parpadear.

### 2. Abrir VS Code en la carpeta del proyecto
Abrir una terminal Bash con `` Ctrl + ` ``.

### 3. Actualizar el código
```bash
git checkout main
git pull
```

Luego, **una** de estas dos opciones:

```bash
# A) Continuar en una rama que ya existe
git checkout feat/nombre-de-la-rama
git merge main            # trae a tu rama lo que subieron tus compañeros
```

```bash
# B) Empezar una funcionalidad nueva
git checkout -b feat/nombre-nuevo
```

### 4. Activar el entorno virtual
```bash
source .venv/Scripts/activate      # Windows (Git Bash)
# source .venv/bin/activate        # Linux / macOS
```
✅ Debe aparecer `(.venv)` al inicio de la línea.

### 5. Encender la base de datos y la API
```bash
docker compose up -d
docker compose ps
```
✅ `microclima_db` y `microclima_api` deben aparecer como **`(healthy)`**.
⏳ Si dice `(health: starting)`, esperar 30 segundos y repetir `docker compose ps`.

### 6. (Opcional) Verificar que todo responde
- API viva: http://localhost:8000/salud → `{"estado":"ok","base_de_datos":"ok"}`
- Documentación interactiva: http://localhost:8000/docs

---

## 🛠️ Durante el trabajo

| Situación | Comando |
|---|---|
| Ver qué archivos cambié | `git status` |
| Ejecutar las pruebas de la API | `cd api && python -m pytest && cd ..` |
| Ver los mensajes (logs) de la API | `docker compose logs -f api` (salir con `Ctrl + C`) |
| Abrí una terminal nueva | `source .venv/Scripts/activate` |

---

## 🌙 Al terminar el día

```bash
git status                       # revisar: el archivo .env NUNCA debe aparecer
git add -A
git commit -m "tipo: descripción corta"
git push                         # la primera vez en una rama: git push -u origin nombre-de-la-rama
docker compose stop              # opcional: apaga los contenedores SIN borrar datos
deactivate                       # opcional: sale del entorno virtual
```

### Tipos de commit
| Tipo | Cuándo usarlo | Ejemplo |
|---|---|---|
| `feat` | Nueva funcionalidad | `feat: lectura del sensor BMP280` |
| `fix` | Corrección de un error | `fix: zona horaria en la comparación` |
| `docs` | Solo documentación | `docs: actualiza el README` |
| `test` | Solo pruebas | `test: prueba de token inválido` |
| `chore` | Mantenimiento / configuración | `chore: actualiza dependencias` |

---

## 🔀 Al terminar una funcionalidad (Pull Request)

1. `git push` de la rama.
2. En GitHub: **Compare & pull request** → completar la plantilla.
3. Revisar la pestaña **Files changed**:
   - [ ] No hay `.env`, contraseñas ni CSV grandes
   - [ ] Solo están los archivos de esta funcionalidad
   - [ ] Las pruebas pasaron
4. **Merge** → volver a la rama principal:
```bash
git checkout main
git pull
```

---

## ⚠️ Situaciones especiales

| Situación | Qué hacer |
|---|---|
| Alguien cambió un `requirements.txt` | `pip install -r requirements.txt -r api/requirements-dev.txt` |
| Alguien cambió el código de `api/` | `docker compose up -d --build` |
| Alguien cambió `db/init/01_esquema.sql` | `docker compose down -v` → `docker compose up -d` → `python data_science/cargar_bd.py` ⚠️ **borra la base** |
| La API no responde | `docker compose logs api` para ver el error |
| Necesito un token nuevo para el ESP32 | `cd api && python -m scripts.crear_token QRO-CENTRO-01 && cd ..` (el anterior deja de funcionar) |

> **¡Cuidado!** `docker compose stop` solo apaga (los datos se conservan).
> `docker compose down -v` **borra la base de datos completa**. Úsalo solo cuando cambie el esquema.

---

## 💡 Consejos

- **Docker se enciende solo:** el `docker-compose.yml` tiene `restart: unless-stopped`, así que al abrir Docker Desktop los contenedores vuelven a encenderse (salvo que se hayan detenido con `stop`).
- **venv automático en VS Code:** `Ctrl + Shift + P` → **Python: Select Interpreter** → elegir el que tiene `.venv` en la ruta. Desde entonces, cada terminal nueva se abre con el entorno activado.
- **Commits pequeños y frecuentes:** es más fácil encontrar errores y el historial queda más claro.
