// Implementación de WiFi, hora (NTP) y envío HTTP a la API.
#include "red.h"

#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>

#include "config.h"
#include "secretos.h"

namespace {

uint32_t ultimoIntentoWifi = 0;

// Agrega un valor numérico al JSON con 1 decimal, o null si no hay dato.
void agregarValor(JsonDocument& documento, const char* clave, float valor) {
    if (isnan(valor)) {
        documento[clave] = nullptr;
    } else {
        documento[clave] = serialized(String(valor, 1));
    }
}

// Fecha en formato ISO 8601 en UTC, ej. 2026-11-19T20:30:00Z (formato que exige la API)
String formatearHoraUtc(time_t instante) {
    struct tm fecha;
    gmtime_r(&instante, &fecha);
    char texto[25];
    strftime(texto, sizeof(texto), "%Y-%m-%dT%H:%M:%SZ", &fecha);
    return String(texto);
}

String construirJson(const Lectura& lectura) {
    const Medicion& m = lectura.medicion;
    JsonDocument documento;
    documento["estacion"] = CODIGO_ESTACION;
    documento["ts"] = formatearHoraUtc(lectura.instante);
    agregarValor(documento, "temperatura_dht", m.temperaturaDht);
    agregarValor(documento, "temperatura_bmp", m.temperaturaBmp);
    // Se prefiere la humedad del BME280 (±3 %) sobre la del DHT11 (±5 %)
    agregarValor(documento, "humedad", isnan(m.humedadBme) ? m.humedadDht : m.humedadBme);
    agregarValor(documento, "presion_hpa", m.presionHpa);
    agregarValor(documento, "iluminancia_lux", m.iluminanciaLux);

    String cuerpo;
    serializeJson(documento, cuerpo);
    return cuerpo;
}

}  // namespace

// ---------------- WiFi ----------------

void iniciarWifi() {
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    ultimoIntentoWifi = millis();

    Serial.printf("Conectando a la red WiFi \"%s\"", WIFI_SSID);
    // Espera hasta 15 s en el arranque; si no conecta, sigue funcionando y reintenta después
    const uint32_t inicio = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - inicio < 15000) {
        delay(500);
        Serial.print(".");
    }
    Serial.println();

    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("[OK] WiFi conectado. IP del ESP32: %s\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("[AVISO] Sin WiFi por ahora. Se reintentara automaticamente.");
    }
}

void mantenerWifi() {
    if (WiFi.status() == WL_CONNECTED) {
        return;
    }
    if (millis() - ultimoIntentoWifi >= INTERVALO_REINTENTO_WIFI_MS) {
        Serial.println("[AVISO] WiFi desconectado. Reintentando...");
        WiFi.disconnect();
        WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
        ultimoIntentoWifi = millis();
    }
}

bool wifiConectado() {
    return WiFi.status() == WL_CONNECTED;
}

// ---------------- Hora ----------------

void iniciarHora() {
    // Sincroniza el reloj por internet (NTP); se vuelve a sincronizar solo cada hora
    configTzTime(ZONA_HORARIA, SERVIDOR_NTP_1, SERVIDOR_NTP_2);
    Serial.print("Sincronizando la hora por NTP");
    const uint32_t inicio = millis();
    while (!horaValida() && millis() - inicio < 15000) {
        delay(500);
        Serial.print(".");
    }
    Serial.println();
    if (horaValida()) {
        Serial.printf("[OK] Hora sincronizada: %s\n", formatearHoraLocal(time(nullptr)).c_str());
    } else {
        Serial.println("[AVISO] Hora aun no sincronizada. No se enviaran lecturas hasta tenerla.");
    }
}

bool horaValida() {
    return time(nullptr) > FECHA_MINIMA_VALIDA;
}

String formatearHoraLocal(time_t instante) {
    struct tm fecha;
    localtime_r(&instante, &fecha);
    char texto[20];
    strftime(texto, sizeof(texto), "%Y-%m-%d %H:%M:%S", &fecha);
    return String(texto);
}

// ---------------- Envío a la API ----------------

ResultadoEnvio enviarLectura(const Lectura& lectura) {
    if (!wifiConectado()) {
        return ResultadoEnvio::ErrorRed;
    }

    HTTPClient http;
    const String url = String(API_URL_BASE) + RUTA_LECTURAS;
    if (!http.begin(url)) {
        return ResultadoEnvio::ErrorRed;
    }
    http.setTimeout(TIEMPO_ESPERA_HTTP_MS);
    http.addHeader("Content-Type", "application/json");
    // El token viaja en la cabecera, nunca se imprime en el Monitor Serial
    http.addHeader("Authorization", String("Bearer ") + API_TOKEN);

    const String cuerpo = construirJson(lectura);
    const int codigo = http.POST(cuerpo);
    const String respuesta = (codigo > 0) ? http.getString() : HTTPClient::errorToString(codigo);
    http.end();

    if (codigo == 201) return ResultadoEnvio::Exito;
    if (codigo == 409) return ResultadoEnvio::Duplicado;
    if (codigo == 401 || codigo == 403) return ResultadoEnvio::ErrorAutenticacion;

    // Para los demás casos se muestra la respuesta para facilitar la depuración
    Serial.printf("  Respuesta de la API (%d): %s\n", codigo, respuesta.c_str());
    if (codigo == 422) {
        Serial.printf("  JSON enviado: %s\n", cuerpo.c_str());
        return ResultadoEnvio::ErrorDatos;
    }
    if (codigo >= 500) return ResultadoEnvio::ErrorServidor;
    return ResultadoEnvio::ErrorRed;
}

const char* describirResultado(ResultadoEnvio resultado) {
    switch (resultado) {
        case ResultadoEnvio::Exito: return "registrada (201)";
        case ResultadoEnvio::Duplicado: return "ya existia (409), se descarta";
        case ResultadoEnvio::ErrorDatos: return "datos rechazados (422), se descarta";
        case ResultadoEnvio::ErrorAutenticacion: return "token invalido (401/403): revise secretos.h";
        case ResultadoEnvio::ErrorServidor: return "error del servidor, se reintentara";
        default: return "sin conexion con la API, se reintentara";
    }
}
