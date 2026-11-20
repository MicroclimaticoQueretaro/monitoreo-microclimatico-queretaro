// Estructuras de datos compartidas entre los módulos del firmware.
#pragma once

#include <Arduino.h>
#include <time.h>

// Una medición de todos los sensores. NAN significa "sin dato".
struct Medicion {
    float temperaturaDht = NAN;
    float humedadDht = NAN;
    float temperaturaBmp = NAN;  // Temperatura del BME280/BMP280
    float humedadBme = NAN;      // Solo existe si el chip es BME280
    float presionHpa = NAN;
    float iluminanciaLux = NAN;
};

// Medición promediada lista para enviar, con su marca de tiempo.
struct Lectura {
    Medicion medicion;
    time_t instante = 0;  // segundos desde 1970 (UTC)
};
