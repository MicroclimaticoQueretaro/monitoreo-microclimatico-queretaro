// Control remoto de la estación por MQTT: el sitio web la activa o la pone en espera.
#pragma once

#include <Arduino.h>

enum class ModoEstacion {
    Midiendo,  // toma muestras y envía lecturas a la API
    EnEspera   // conectada, pero sin medir: espera la orden "activar"
};

// Configura el cliente MQTT. Si MQTT_HOST está vacío en secretos.h, el control
// remoto queda desactivado y la estación mide siempre (comportamiento anterior).
void iniciarControl();

// Mantiene la conexión con el broker y procesa las órdenes recibidas. No bloquea
// salvo al reconectar (cada pocos segundos, solo si se perdió la conexión).
void mantenerControl();

ModoEstacion modoActual();
bool controlRemotoHabilitado();
bool controlConectado();
