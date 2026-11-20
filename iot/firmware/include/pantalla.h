// Pantalla LCD I2C (16x2) que muestra las mediciones y el estado de la estación.
#pragma once

#include "tipos.h"

// Inicia el bus I2C del LCD (Wire, GPIO 21/22), detecta la pantalla y la enciende.
void inicializarPantalla();

// Muestra un mensaje fijo de dos líneas (ej. durante el arranque).
void mostrarMensajePantalla(const char* linea1, const char* linea2);

// Rota entre las páginas de información. No bloquea: si todavía no toca
// cambiar de página, regresa inmediatamente.
void actualizarPantalla(const Medicion& ultimaMuestra, const EstadoSistema& estado);
