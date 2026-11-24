// Implementación del control remoto por MQTT (broker EMQX Cloud Serverless, con TLS).
//
// Temas:
//   <prefijo>/<estación>/comando -> la API publica {"accion":"activar"|"detener"} (retenido)
//   <prefijo>/<estación>/estado  -> la estación publica {"estado":"midiendo"|"en_espera"} (retenido)
// Si la estación se desconecta sin avisar, el broker publica por ella
// {"estado":"desconectado"} (mensaje de "último deseo", LWT).
#include "control.h"

#include <ArduinoJson.h>
#include <Preferences.h>
#include <PubSubClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

#include "certificados.h"
#include "config.h"
#include "red.h"
#include "secretos.h"

// Valores por defecto si secretos.h aún no tiene la sección MQTT
#ifndef MQTT_HOST
#define MQTT_HOST ""
#endif
#ifndef MQTT_PUERTO
#define MQTT_PUERTO 8883
#endif
#ifndef MQTT_USUARIO
#define MQTT_USUARIO ""
#endif
#ifndef MQTT_CONTRASENA
#define MQTT_CONTRASENA ""
#endif
#ifndef MQTT_TLS
#define MQTT_TLS 1
#endif

namespace {

WiFiClientSecure clienteSeguro;
WiFiClient clienteNormal;
PubSubClient mqtt;
Preferences memoria;  // memoria no volátil (NVS): recuerda el modo tras un reinicio

ModoEstacion modo = ModoEstacion::Midiendo;
bool habilitado = false;
uint32_t ultimoIntento = 0;
bool primerIntento = true;
String temaComando;
String temaEstado;

const char* nombreModo(ModoEstacion m) {
    return m == ModoEstacion::Midiendo ? "midiendo" : "en_espera";
}

// Publica el modo actual como mensaje retenido, con la hora en UTC si ya está sincronizada
void publicarEstado() {
    if (!mqtt.connected()) {
        return;
    }
    JsonDocument documento;
    documento["estado"] = nombreModo(modo);
    const time_t ahora = time(nullptr);
    if (ahora > FECHA_MINIMA_VALIDA) {
        struct tm fecha;
        gmtime_r(&ahora, &fecha);
        char texto[25];
        strftime(texto, sizeof(texto), "%Y-%m-%dT%H:%M:%SZ", &fecha);
        documento["ts"] = texto;
    }
    char carga[96];
    const size_t largo = serializeJson(documento, carga, sizeof(carga));
    mqtt.publish(temaEstado.c_str(), reinterpret_cast<const uint8_t*>(carga), largo, true);
}

void cambiarModo(ModoEstacion nuevo) {
    if (nuevo != modo) {
        modo = nuevo;
        memoria.putBool("midiendo", modo == ModoEstacion::Midiendo);
        Serial.printf("[CONTROL] Nuevo modo: %s\n", nombreModo(modo));
    }
    publicarEstado();  // confirma al sitio el modo actual
}

// Se ejecuta cada vez que llega un mensaje al tema de comandos
void alRecibirMensaje(char* tema, uint8_t* carga, unsigned int largo) {
    (void)tema;
    String accion;
    JsonDocument documento;
    if (deserializeJson(documento, carga, largo) == DeserializationError::Ok && documento["accion"].is<const char*>()) {
        accion = documento["accion"].as<const char*>();
    } else {
        // También se acepta texto plano ("activar"); la carga NO termina en '\0'
        for (unsigned int i = 0; i < largo; i++) {
            accion += static_cast<char>(carga[i]);
        }
        accion.trim();
    }

    if (accion == "activar") {
        cambiarModo(ModoEstacion::Midiendo);
    } else if (accion == "detener") {
        cambiarModo(ModoEstacion::EnEspera);
    } else {
        Serial.printf("[CONTROL] Orden desconocida ignorada: %s\n", accion.c_str());
    }
}

void conectar() {
    const String idCliente = String("esp32-") + CODIGO_ESTACION;
    const char* ultimoDeseo = "{\"estado\":\"desconectado\"}";
    Serial.printf("[CONTROL] Conectando al broker MQTT %s:%d...\n", MQTT_HOST, MQTT_PUERTO);
    // connect(id, usuario, contraseña, tema LWT, QoS LWT, retener LWT, mensaje LWT)
    if (mqtt.connect(idCliente.c_str(), MQTT_USUARIO, MQTT_CONTRASENA, temaEstado.c_str(), 1, true, ultimoDeseo)) {
        mqtt.subscribe(temaComando.c_str(), 1);
        Serial.printf("[CONTROL] Conectado. Escuchando ordenes en %s\n", temaComando.c_str());
        publicarEstado();
    } else {
        // Códigos de PubSubClient: -2 red/TLS, 4 usuario o contraseña incorrectos, 5 no autorizado
        Serial.printf("[CONTROL] No se pudo conectar (codigo %d). Se reintentara.\n", mqtt.state());
    }
}

}  // namespace

void iniciarControl() {
    habilitado = strlen(MQTT_HOST) > 0;
    if (!habilitado) {
        modo = ModoEstacion::Midiendo;
        Serial.println("[CONTROL] MQTT no configurado: la estacion mide siempre.");
        return;
    }

    // Arranca en el último modo guardado; el comando retenido del broker lo confirma al conectar
    memoria.begin("control", false);
    modo = memoria.getBool("midiendo", false) ? ModoEstacion::Midiendo : ModoEstacion::EnEspera;
    Serial.printf("[CONTROL] Modo al iniciar: %s\n", nombreModo(modo));

    temaComando = String(MQTT_PREFIJO) + "/" + CODIGO_ESTACION + "/comando";
    temaEstado = String(MQTT_PREFIJO) + "/" + CODIGO_ESTACION + "/estado";

    if (MQTT_TLS) {
        clienteSeguro.setCACert(CERTIFICADOS_RAIZ);  // EMQX Cloud usa un certificado firmado por DigiCert
        mqtt.setClient(clienteSeguro);
    } else {
        mqtt.setClient(clienteNormal);
    }
    mqtt.setServer(MQTT_HOST, MQTT_PUERTO);
    mqtt.setCallback(alRecibirMensaje);
    mqtt.setBufferSize(512);
    mqtt.setKeepAlive(MQTT_KEEPALIVE_S);
    mqtt.setSocketTimeout(10);
}

void mantenerControl() {
    if (!habilitado) {
        return;
    }
    if (mqtt.connected()) {
        mqtt.loop();  // procesa los mensajes que llegaron
        return;
    }
    // TLS necesita WiFi y la hora correcta (para validar el certificado)
    if (!wifiConectado() || !horaValida()) {
        return;
    }
    if (!primerIntento && millis() - ultimoIntento < MQTT_INTERVALO_REINTENTO_MS) {
        return;
    }
    primerIntento = false;
    ultimoIntento = millis();
    conectar();
}

ModoEstacion modoActual() {
    return modo;
}

bool controlRemotoHabilitado() {
    return habilitado;
}

bool controlConectado() {
    return habilitado && mqtt.connected();
}
