// =====================================================================
// Estación meteorológica IoT — Monitoreo Microclimático de Querétaro
// ESP32 DevKit V1 + DHT11 + BME280/BMP280 + BH1750 (GY-302)
//
// Flujo: muestra cada 5 s -> promedio cada 60 s -> cola -> envío HTTP a la API.
// Si se pierde la conexión, las lecturas esperan en la cola y se envían después.
// =====================================================================
#include <Arduino.h>

#include "config.h"
#include "red.h"
#include "sensores.h"

namespace {

Promediador promediador;
uint32_t ultimoMuestreo = 0;
uint32_t ultimoPromedio = 0;
uint32_t ultimoIntentoEnvio = 0;
bool esperarTrasFallo = false;

// ---------- Cola circular de lecturas pendientes de envío ----------
Lectura cola[TAMANO_COLA];
size_t inicioCola = 0;
size_t cantidadEnCola = 0;

void encolar(const Lectura& lectura) {
    if (cantidadEnCola == TAMANO_COLA) {
        // Cola llena: se descarta la lectura más antigua para hacer espacio
        inicioCola = (inicioCola + 1) % TAMANO_COLA;
        cantidadEnCola--;
        Serial.println("[AVISO] Cola llena: se descarto la lectura mas antigua.");
    }
    cola[(inicioCola + cantidadEnCola) % TAMANO_COLA] = lectura;
    cantidadEnCola++;
}

void quitarPrimera() {
    inicioCola = (inicioCola + 1) % TAMANO_COLA;
    cantidadEnCola--;
}

// ---------- Monitor Serial ----------
void imprimirValor(const char* etiqueta, float valor, const char* unidad) {
    if (isnan(valor)) {
        Serial.printf("  %-20s sin dato\n", etiqueta);
    } else {
        Serial.printf("  %-20s %.1f %s\n", etiqueta, valor, unidad);
    }
}

void imprimirLectura(const Lectura& lectura, uint16_t muestras) {
    const Medicion& m = lectura.medicion;
    Serial.println();
    Serial.println("========== PROMEDIO DEL MINUTO ==========");
    if (horaValida()) {
        Serial.printf("  Hora local:          %s\n", formatearHoraLocal(lectura.instante).c_str());
    }
    Serial.printf("  Muestras promediadas: %u\n", muestras);
    imprimirValor("Temperatura DHT11:", m.temperaturaDht, "C");
    imprimirValor("Humedad DHT11:", m.humedadDht, "%");
    imprimirValor("Temperatura BME/BMP:", m.temperaturaBmp, "C");
    imprimirValor("Humedad BME280:", m.humedadBme, "%");
    imprimirValor("Presion:", m.presionHpa, "hPa");
    imprimirValor("Iluminancia:", m.iluminanciaLux, "lux");
    Serial.println("=========================================");
}

// ---------- Tareas del ciclo principal ----------
void tomarMuestraSiCorresponde() {
    if (millis() - ultimoMuestreo >= INTERVALO_MUESTREO_MS) {
        ultimoMuestreo = millis();
        promediador.agregar(leerSensores());
    }
}

void cerrarPromedioSiCorresponde() {
    if (millis() - ultimoPromedio < INTERVALO_ENVIO_MS) {
        return;
    }
    ultimoPromedio = millis();

    Lectura lectura;
    lectura.medicion = promediador.promedio();
    lectura.instante = time(nullptr);
    imprimirLectura(lectura, promediador.cantidadMuestras());
    promediador.reiniciar();

    if (!ENVIAR_A_API) {
        return;
    }
    // Sin hora real la API no puede ubicar la lectura en el tiempo: se descarta
    if (!horaValida()) {
        Serial.println("[AVISO] Reloj sin sincronizar: lectura descartada.");
        return;
    }
    encolar(lectura);
}

void enviarPendientesSiCorresponde() {
    if (!ENVIAR_A_API || cantidadEnCola == 0 || !wifiConectado()) {
        return;
    }
    // Tras un fallo se espera un poco antes de reintentar (no saturar la red ni la API)
    const uint32_t espera = esperarTrasFallo ? ESPERA_TRAS_FALLO_ENVIO_MS : 1000;
    if (millis() - ultimoIntentoEnvio < espera) {
        return;
    }
    ultimoIntentoEnvio = millis();

    const ResultadoEnvio resultado = enviarLectura(cola[inicioCola]);
    Serial.printf("[ENVIO] Lectura de %s: %s | pendientes: %u\n",
                  formatearHoraLocal(cola[inicioCola].instante).c_str(),
                  describirResultado(resultado), static_cast<unsigned>(cantidadEnCola));

    switch (resultado) {
        case ResultadoEnvio::Exito:
        case ResultadoEnvio::Duplicado:
        case ResultadoEnvio::ErrorDatos:  // reintentar no la corregiría
            quitarPrimera();
            esperarTrasFallo = false;
            break;
        default:  // red, servidor o token: se conserva para reintentar
            esperarTrasFallo = true;
            break;
    }
}

}  // namespace

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println();
    Serial.println("=========================================");
    Serial.println("   ESTACION METEOROLOGICA - QUERETARO");
    Serial.printf("   Estacion: %s\n", CODIGO_ESTACION);
    Serial.println("=========================================");

    inicializarSensores();

    if (ENVIAR_A_API) {
        iniciarWifi();
        iniciarHora();
    } else {
        Serial.println("[MODO PRUEBA] Envio a la API desactivado (ENVIAR_A_API = false).");
    }

    ultimoPromedio = millis();
    Serial.printf("\nMuestra cada %lu s, promedio y envio cada %lu s.\n",
                  INTERVALO_MUESTREO_MS / 1000UL, INTERVALO_ENVIO_MS / 1000UL);
}

void loop() {
    // Ninguna tarea bloquea: el ciclo revisa qué toca hacer en cada vuelta
    if (ENVIAR_A_API) {
        mantenerWifi();
    }
    tomarMuestraSiCorresponde();
    cerrarPromedioSiCorresponde();
    enviarPendientesSiCorresponde();
}
