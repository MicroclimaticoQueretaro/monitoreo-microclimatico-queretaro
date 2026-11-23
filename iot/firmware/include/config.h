// =====================================================================
// Configuración general del firmware (NO contiene secretos)
// Las contraseñas y el token van en include/secretos.h (fuera de Git).
// =====================================================================
#pragma once

#include <Arduino.h>

// ---------- Pines (iguales al montaje de la protoboard) ----------
// El ESP32 tiene dos buses I2C. Se usa uno para los sensores y otro para el LCD:
// así los 5 V del adaptador del LCD quedan aislados del bus de los sensores (3.3 V).
constexpr uint8_t PIN_DHT = 27;            // Datos del DHT11
constexpr uint8_t PIN_SDA = 25;            // Bus I2C de sensores (Wire1): BME280/BMP280 y BH1750
constexpr uint8_t PIN_SCL = 26;
constexpr uint8_t PIN_SDA_LCD = 21;        // Bus I2C del LCD (Wire)
constexpr uint8_t PIN_SCL_LCD = 22;
constexpr uint8_t DIRECCION_BH1750 = 0x23; // Pin ADDR del GY-302 desconectado o a GND

// ---------- Pantalla LCD I2C (bus propio en GPIO 21/22) ----------
constexpr bool USAR_LCD = true;
constexpr uint8_t LCD_COLUMNAS = 16;
constexpr uint8_t LCD_FILAS = 2;
// Direcciones típicas del adaptador PCF8574: se prueban en orden hasta encontrar la pantalla
constexpr uint8_t LCD_DIRECCIONES[] = {0x27, 0x3F};
constexpr uint32_t INTERVALO_PAGINA_LCD_MS = 3000;  // cambia de página cada 3 s

// ---------- Estación ----------
constexpr char CODIGO_ESTACION[] = "QRO-CENTRO-01";
constexpr char RUTA_LECTURAS[] = "/api/v1/lecturas";

// ---------- Modo de funcionamiento ----------
// false = solo lee los sensores y los muestra en el Monitor Serial (sin WiFi ni API).
// Útil para probar el hardware antes de configurar la red.
constexpr bool ENVIAR_A_API = true;

// ---------- Tiempos ----------
// Se toma una muestra cada 5 s y se envía el PROMEDIO cada 60 s:
// promediar reduce el ruido de los sensores (sobre todo del DHT11).
constexpr uint32_t INTERVALO_MUESTREO_MS = 5000;
constexpr uint32_t INTERVALO_ENVIO_MS = 60000;
constexpr uint32_t INTERVALO_REINTENTO_WIFI_MS = 30000;
constexpr uint32_t ESPERA_TRAS_FALLO_ENVIO_MS = 15000;
// 20 s: en la nube gratuita la API puede tardar en responder si estaba dormida
constexpr uint16_t TIEMPO_ESPERA_HTTP_MS = 20000;

// Lecturas guardadas en memoria si no hay conexión (60 = 1 hora a 1 lectura/min).
// Cuando la cola se llena, se descarta la más antigua.
constexpr size_t TAMANO_COLA = 60;

// ---------- Hora (NTP) ----------
// Centro de México: UTC-6 sin horario de verano (abolido en 2022)
constexpr char ZONA_HORARIA[] = "CST6";
constexpr char SERVIDOR_NTP_1[] = "pool.ntp.org";
constexpr char SERVIDOR_NTP_2[] = "time.google.com";
// Cualquier fecha anterior a 2024 significa que el reloj aún no se sincronizó
constexpr time_t FECHA_MINIMA_VALIDA = 1704067200;  // 2024-01-01 00:00 UTC

// ---------- Rangos físicos válidos (iguales a los de la API) ----------
// Un valor fuera de rango se descarta (se envía como null) en lugar de
// hacer que la API rechace la lectura completa.
constexpr float TEMPERATURA_MIN = -10.0f, TEMPERATURA_MAX = 60.0f;
constexpr float HUMEDAD_MIN = 0.0f, HUMEDAD_MAX = 100.0f;
constexpr float PRESION_MIN_HPA = 700.0f, PRESION_MAX_HPA = 1100.0f;
constexpr float ILUMINANCIA_MIN = 0.0f, ILUMINANCIA_MAX = 200000.0f;
