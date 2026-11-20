// Lectura de los sensores y promedio de muestras.
#pragma once

#include "tipos.h"

// Inicia el bus I2C y detecta los sensores conectados.
void inicializarSensores();

// Lee todos los sensores una vez. Los valores inválidos quedan como NAN.
Medicion leerSensores();

// Nombre del chip de presión detectado ("BME280", "BMP280" o "ninguno").
const char* nombreChipPresion();

// Acumula muestras y calcula el promedio de cada variable por separado,
// ignorando las muestras sin dato (NAN).
class Promediador {
public:
    void agregar(const Medicion& muestra);
    Medicion promedio() const;
    void reiniciar();
    uint16_t cantidadMuestras() const { return totalMuestras_; }

private:
    static constexpr uint8_t NUM_VARIABLES = 6;
    float suma_[NUM_VARIABLES] = {0};
    uint16_t conteo_[NUM_VARIABLES] = {0};
    uint16_t totalMuestras_ = 0;
};
