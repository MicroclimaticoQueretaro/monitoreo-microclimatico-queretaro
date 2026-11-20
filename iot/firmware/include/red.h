// Conexión WiFi, sincronización de hora y envío de lecturas a la API.
#pragma once

#include "tipos.h"

void iniciarWifi();
void mantenerWifi();          // Reconecta sin bloquear si se perdió la señal
bool wifiConectado();

void iniciarHora();           // Configura NTP y la zona horaria
bool horaValida();            // true cuando el reloj ya se sincronizó
String formatearHoraLocal(time_t instante);

enum class ResultadoEnvio {
    Exito,              // 201: registrada
    Duplicado,          // 409: ya existía (se considera enviada)
    ErrorDatos,         // 422: la API la rechazó; reintentar no sirve
    ErrorAutenticacion, // 401/403: revisar el token en secretos.h
    ErrorServidor,      // 5xx: reintentar más tarde
    ErrorRed            // Sin conexión o tiempo agotado: reintentar más tarde
};

ResultadoEnvio enviarLectura(const Lectura& lectura);
const char* describirResultado(ResultadoEnvio resultado);
