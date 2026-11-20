# Firmware — Estación ESP32

Firmware de la estación meteorológica, desarrollado con **PlatformIO** (framework Arduino).
Toma una muestra cada 5 s, envía el **promedio de cada minuto** a la API y guarda hasta
1 hora de lecturas en memoria si se pierde la conexión.

## Hardware

| Componente | Variable | Conexión |
|---|---|---|
| ESP32 DevKit V1 (30 pines) | Microcontrolador con WiFi | — |
| DHT11 | Temperatura, humedad | Datos → **GPIO 27** |
| BME280 / BMP280 (I²C, 0x76 o 0x77) | Temperatura, presión (y humedad si es BME280) | Bus de sensores: SDA → **GPIO 25**, SCL → **GPIO 26** |
| GY-302 / BH1750 (I²C, 0x23) | Iluminancia (lux) | Bus de sensores: SDA → **GPIO 25**, SCL → **GPIO 26** |
| LCD 16x2 con adaptador I²C (0x27 o 0x3F) | Muestra mediciones y estado | Bus del LCD: SDA → **GPIO 21**, SCL → **GPIO 22** |

> Los sensores se alimentan con **3.3 V** (pin `3V3`); el LCD con **5 V**. Todos comparten **GND**.
> Se usan **dos buses I²C** del ESP32 para que el adaptador del LCD (con resistencias pull-up a 5 V)
> no afecte el bus de los sensores. Los pines del ESP32 trabajan a 3.3 V: para la instalación
> definitiva se recomienda un **conversor de nivel lógico** entre el ESP32 y el LCD.

El firmware detecta automáticamente si el módulo morado tiene un chip **BME280** o **BMP280**.

## Estructura

```
iot/firmware/
├── platformio.ini            # Placa, bibliotecas y velocidad del monitor serial
├── include/
│   ├── config.h              # Pines, intervalos y rangos (sin secretos)
│   ├── secretos.h.example    # Plantilla de WiFi y token (copiar a secretos.h)
│   ├── tipos.h               # Estructuras Medicion y Lectura
│   ├── sensores.h            # Interfaz de los sensores
│   ├── pantalla.h            # Interfaz de la pantalla LCD
│   └── red.h                 # Interfaz de WiFi, NTP y API
└── src/
    ├── main.cpp              # Ciclo principal no bloqueante y cola de envío
    ├── sensores.cpp          # Lectura, validación de rangos y promedio
    ├── pantalla.cpp          # Páginas rotativas del LCD (sin bloquear)
    └── red.cpp               # WiFi, hora NTP y envío HTTP con token
```

## Pantalla LCD

La pantalla rota cada 3 s entre tres páginas, **sin detener** la medición ni el envío:

| Página | Línea 1 | Línea 2 |
|---|---|---|
| Clima | `Temp: 24.6°C` | `Hum:  38.0 %` |
| Presión y luz | `Pres:823.5hPa` | `Luz:  7.5 lx` |
| Estado | `21:49  WiFi:OK` | `Env:123 Pend:0` |

- Muestra la **muestra más reciente** (se actualiza cada 5 s); a la API se envía el **promedio** del minuto.
- `Env` = lecturas registradas en la API desde el encendido; `Pend` = lecturas en cola esperando conexión.
- Si la pantalla no se detecta, la estación sigue funcionando normalmente.
- Se desactiva con `USAR_LCD = false` en `config.h`.

> **Importante:** la biblioteca del LCD usa siempre el bus `Wire` y llama a `Wire.begin()` sin pines.
> Por eso el firmware inicia `Wire` en GPIO 21/22 antes de crear la pantalla, y los sensores usan `Wire1`.

## Configuración

1. Copiar la plantilla de secretos y completarla:
   ```bash
   cp iot/firmware/include/secretos.h.example iot/firmware/include/secretos.h
   ```
   - `WIFI_SSID` / `WIFI_PASSWORD`: red de **2.4 GHz** (el ESP32 no soporta 5 GHz).
   - `API_URL_BASE`: `http://<IP de la computadora>:8000` (ver `ipconfig` en Windows).
   - `API_TOKEN`: generado con `python -m scripts.crear_token QRO-CENTRO-01`.
2. En el `.env` de la raíz, poner `API_HOST_BIND=0.0.0.0` y ejecutar `docker compose up -d`
   para que la API acepte conexiones desde la red local.

Para probar **solo los sensores** (sin WiFi ni API), cambiar en `config.h`:
```cpp
constexpr bool ENVIAR_A_API = false;
```

## Compilar y cargar

En VS Code, abrir el archivo `monitoreo-microclimatico-queretaro.code-workspace` de la raíz
(**File → Open Workspace from File**) para que PlatformIO reconozca el firmware, y usar la barra inferior:
**✓ Build** → **→ Upload** → **🔌 Serial Monitor**.

## Salida esperada en el Monitor Serial

```
[OK] DHT11 configurado en GPIO27
[OK] BH1750 (GY-302) detectado en 0x23
[OK] BME280 detectado en 0x76 (temperatura, humedad y presion)
[OK] WiFi conectado. IP del ESP32: 192.168.1.57
[OK] Hora sincronizada: 2026-11-19 20:45:12

========== PROMEDIO DEL MINUTO ==========
  Muestras promediadas: 12
  Temperatura DHT11:   22.0 C
  ...
[ENVIO] Lectura de 2026-11-19 20:46:12: registrada (201) | pendientes: 1
```

## Solución de problemas

| Mensaje | Causa probable |
|---|---|
| `No se detecto BME280 ni BMP280` / `BH1750 no detectado` | Cables SDA/SCL invertidos o sin alimentación |
| `Sin WiFi por ahora` | Red de 5 GHz, contraseña incorrecta o fuera de alcance |
| `sin conexion con la API` | IP incorrecta en `API_URL_BASE`, `API_HOST_BIND` no configurado o firewall de Windows |
| `token invalido (401/403)` | Token incorrecto o regenerado: actualizar `secretos.h` |
| `datos rechazados (422)` | Ver el JSON impreso; normalmente reloj sin sincronizar |

## Seguridad

- El WiFi y el token viven en `include/secretos.h`, que está en `.gitignore`.
- El token nunca se imprime en el Monitor Serial.
- En la red local la comunicación es HTTP. Para un despliegue en internet se debe usar **HTTPS**
  (el token viajaría en texto plano por HTTP).
