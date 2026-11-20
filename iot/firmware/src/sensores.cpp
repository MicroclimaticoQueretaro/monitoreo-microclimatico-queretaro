// Implementación de la lectura de sensores.
#include "sensores.h"

#include <Adafruit_BME280.h>
#include <Adafruit_BMP280.h>
#include <BH1750.h>
#include <DHT.h>
#include <Wire.h>

#include "config.h"

namespace {

// Los sensores I2C usan el segundo bus del ESP32 (Wire1); el primero (Wire) es del LCD
TwoWire& busSensores = Wire1;

DHT dht(PIN_DHT, DHT11);
Adafruit_BME280 bme;
Adafruit_BMP280 bmp(&Wire1);
BH1750 medidorLuz;

enum class ChipPresion { Ninguno, BME280, BMP280 };
ChipPresion chipPresion = ChipPresion::Ninguno;
bool bh1750Disponible = false;

// Devuelve el valor si está dentro del rango físico; si no, NAN (sin dato).
float validarRango(float valor, float minimo, float maximo) {
    if (isnan(valor) || valor < minimo || valor > maximo) {
        return NAN;
    }
    return valor;
}

// El módulo morado "BME/BMP280" puede traer cualquiera de los dos chips,
// en la dirección 0x76 o 0x77. Se prueban todas las combinaciones.
void detectarChipPresion() {
    const uint8_t direcciones[] = {0x76, 0x77};

    for (uint8_t direccion : direcciones) {
        if (bme.begin(direccion, &busSensores)) {
            chipPresion = ChipPresion::BME280;
            // Configuración recomendada por Bosch para estaciones meteorológicas:
            // modo forzado (mide solo cuando se pide) para reducir el autocalentamiento.
            bme.setSampling(Adafruit_BME280::MODE_FORCED,
                            Adafruit_BME280::SAMPLING_X1,   // temperatura
                            Adafruit_BME280::SAMPLING_X1,   // presión
                            Adafruit_BME280::SAMPLING_X1,   // humedad
                            Adafruit_BME280::FILTER_OFF);
            Serial.printf("[OK] BME280 detectado en 0x%02X (temperatura, humedad y presion)\n", direccion);
            return;
        }
    }

    for (uint8_t direccion : direcciones) {
        if (bmp.begin(direccion)) {
            chipPresion = ChipPresion::BMP280;
            bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,
                            Adafruit_BMP280::SAMPLING_X2,   // temperatura
                            Adafruit_BMP280::SAMPLING_X16,  // presión
                            Adafruit_BMP280::FILTER_X16,
                            Adafruit_BMP280::STANDBY_MS_1000);
            Serial.printf("[OK] BMP280 detectado en 0x%02X (temperatura y presion)\n", direccion);
            return;
        }
    }

    Serial.println("[ERROR] No se detecto BME280 ni BMP280. Revise el cableado SDA/SCL y la alimentacion.");
}

}  // namespace

void inicializarSensores() {
    busSensores.begin(PIN_SDA, PIN_SCL);
    Serial.printf("Bus I2C de sensores en SDA=GPIO%u, SCL=GPIO%u\n", PIN_SDA, PIN_SCL);

    dht.begin();
    Serial.printf("[OK] DHT11 configurado en GPIO%u\n", PIN_DHT);

    bh1750Disponible = medidorLuz.begin(BH1750::CONTINUOUS_HIGH_RES_MODE, DIRECCION_BH1750, &busSensores);
    if (bh1750Disponible) {
        Serial.printf("[OK] BH1750 (GY-302) detectado en 0x%02X\n", DIRECCION_BH1750);
    } else {
        Serial.println("[ERROR] BH1750 no detectado. Revise el cableado y el pin ADDR.");
    }

    detectarChipPresion();
}

Medicion leerSensores() {
    Medicion m;

    // DHT11: devuelve NAN si la lectura falla
    m.temperaturaDht = validarRango(dht.readTemperature(), TEMPERATURA_MIN, TEMPERATURA_MAX);
    m.humedadDht = validarRango(dht.readHumidity(), HUMEDAD_MIN, HUMEDAD_MAX);

    // BH1750: devuelve un valor negativo si hay error
    if (bh1750Disponible) {
        m.iluminanciaLux = validarRango(medidorLuz.readLightLevel(), ILUMINANCIA_MIN, ILUMINANCIA_MAX);
    }

    if (chipPresion == ChipPresion::BME280) {
        // En modo forzado hay que pedir una medición nueva antes de leer
        if (bme.takeForcedMeasurement()) {
            m.temperaturaBmp = validarRango(bme.readTemperature(), TEMPERATURA_MIN, TEMPERATURA_MAX);
            m.humedadBme = validarRango(bme.readHumidity(), HUMEDAD_MIN, HUMEDAD_MAX);
            m.presionHpa = validarRango(bme.readPressure() / 100.0f, PRESION_MIN_HPA, PRESION_MAX_HPA);
        }
    } else if (chipPresion == ChipPresion::BMP280) {
        m.temperaturaBmp = validarRango(bmp.readTemperature(), TEMPERATURA_MIN, TEMPERATURA_MAX);
        m.presionHpa = validarRango(bmp.readPressure() / 100.0f, PRESION_MIN_HPA, PRESION_MAX_HPA);
    }

    return m;
}

const char* nombreChipPresion() {
    switch (chipPresion) {
        case ChipPresion::BME280: return "BME280";
        case ChipPresion::BMP280: return "BMP280";
        default: return "ninguno";
    }
}

// ---------------- Promediador ----------------

namespace {
// Convierte la medición en un arreglo para poder recorrer las 6 variables con un ciclo
void aArreglo(const Medicion& m, float (&valores)[6]) {
    valores[0] = m.temperaturaDht;
    valores[1] = m.humedadDht;
    valores[2] = m.temperaturaBmp;
    valores[3] = m.humedadBme;
    valores[4] = m.presionHpa;
    valores[5] = m.iluminanciaLux;
}
}  // namespace

void Promediador::agregar(const Medicion& muestra) {
    float valores[NUM_VARIABLES];
    aArreglo(muestra, valores);
    for (uint8_t i = 0; i < NUM_VARIABLES; i++) {
        if (!isnan(valores[i])) {
            suma_[i] += valores[i];
            conteo_[i]++;
        }
    }
    totalMuestras_++;
}

Medicion Promediador::promedio() const {
    float resultado[NUM_VARIABLES];
    for (uint8_t i = 0; i < NUM_VARIABLES; i++) {
        resultado[i] = (conteo_[i] > 0) ? suma_[i] / conteo_[i] : NAN;
    }
    Medicion m;
    m.temperaturaDht = resultado[0];
    m.humedadDht = resultado[1];
    m.temperaturaBmp = resultado[2];
    m.humedadBme = resultado[3];
    m.presionHpa = resultado[4];
    m.iluminanciaLux = resultado[5];
    return m;
}

void Promediador::reiniciar() {
    for (uint8_t i = 0; i < NUM_VARIABLES; i++) {
        suma_[i] = 0;
        conteo_[i] = 0;
    }
    totalMuestras_ = 0;
}
