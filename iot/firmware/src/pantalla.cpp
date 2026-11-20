// Implementación de la pantalla LCD I2C.
#include "pantalla.h"

#include <LiquidCrystal_I2C.h>
#include <Wire.h>

#include "config.h"

namespace {

// Se crea solo si la pantalla responde; si no, la estación funciona sin ella
LiquidCrystal_I2C* lcd = nullptr;

constexpr uint8_t NUM_PAGINAS = 3;
uint8_t paginaActual = 0;
uint32_t ultimoCambioPagina = 0;

// Símbolo de grados en la tabla de caracteres del LCD (0xDF).
// Se separa en dos cadenas para que el compilador no lea "\xDFC" como un solo número.
constexpr char GRADOS_C[] = "\xDF" "C";

bool dispositivoResponde(uint8_t direccion) {
    Wire.beginTransmission(direccion);
    return Wire.endTransmission() == 0;
}

// Escribe la línea completa rellenando con espacios: borra restos del texto
// anterior sin usar lcd->clear(), que hace parpadear la pantalla.
void escribirLinea(uint8_t fila, const char* texto) {
    char linea[LCD_COLUMNAS + 1];
    snprintf(linea, sizeof(linea), "%-*s", static_cast<int>(LCD_COLUMNAS), texto);
    lcd->setCursor(0, fila);
    lcd->print(linea);
}

// Arma "prefijo + valor + unidad", o "prefijo + --" si no hay dato.
void formatearValor(char* destino, size_t tamano, const char* prefijo,
                    float valor, int decimales, const char* unidad) {
    if (isnan(valor)) {
        snprintf(destino, tamano, "%s--", prefijo);
    } else {
        snprintf(destino, tamano, "%s%.*f%s", prefijo, decimales, valor, unidad);
    }
}

void mostrarPaginaClima(const Medicion& m) {
    // Se prefieren los valores del BME280 (más precisos) y, si faltan, los del DHT11
    const float temperatura = isnan(m.temperaturaBmp) ? m.temperaturaDht : m.temperaturaBmp;
    const float humedad = isnan(m.humedadBme) ? m.humedadDht : m.humedadBme;
    char linea1[32];
    char linea2[32];
    formatearValor(linea1, sizeof(linea1), "Temp: ", temperatura, 1, GRADOS_C);
    formatearValor(linea2, sizeof(linea2), "Hum:  ", humedad, 1, " %");
    escribirLinea(0, linea1);
    escribirLinea(1, linea2);
}

void mostrarPaginaPresionLuz(const Medicion& m) {
    char linea1[32];
    char linea2[32];
    formatearValor(linea1, sizeof(linea1), "Pres:", m.presionHpa, 1, "hPa");
    // Con mucha luz se omiten los decimales para que quepa en 16 columnas
    const int decimalesLuz = (!isnan(m.iluminanciaLux) && m.iluminanciaLux >= 1000.0f) ? 0 : 1;
    formatearValor(linea2, sizeof(linea2), "Luz:  ", m.iluminanciaLux, decimalesLuz, " lx");
    escribirLinea(0, linea1);
    escribirLinea(1, linea2);
}

void mostrarPaginaEstado(const EstadoSistema& e) {
    char linea1[32];
    char linea2[32];
    if (e.horaValida) {
        struct tm fecha;
        localtime_r(&e.ahora, &fecha);
        snprintf(linea1, sizeof(linea1), "%02d:%02d  WiFi:%s", fecha.tm_hour, fecha.tm_min,
                 e.wifiConectado ? "OK" : "--");
    } else {
        snprintf(linea1, sizeof(linea1), "--:--  WiFi:%s", e.wifiConectado ? "OK" : "--");
    }
    snprintf(linea2, sizeof(linea2), "Env:%lu Pend:%u",
             static_cast<unsigned long>(e.enviosExitosos),
             static_cast<unsigned>(e.lecturasPendientes));
    escribirLinea(0, linea1);
    escribirLinea(1, linea2);
}

}  // namespace

void inicializarPantalla() {
    if (!USAR_LCD) {
        return;
    }
    // Se inicia el bus del LCD con sus pines ANTES de crear la pantalla:
    // init() de la biblioteca llama a Wire.begin() sin pines y, como el bus ya
    // está iniciado, se conservan GPIO 21/22 (si no, usaría los pines por defecto).
    Wire.begin(PIN_SDA_LCD, PIN_SCL_LCD);
    for (uint8_t direccion : LCD_DIRECCIONES) {
        if (dispositivoResponde(direccion)) {
            lcd = new LiquidCrystal_I2C(direccion, LCD_COLUMNAS, LCD_FILAS);
            lcd->init();
            lcd->backlight();
            Serial.printf("[OK] Pantalla LCD detectada en 0x%02X\n", direccion);
            mostrarMensajePantalla("Estacion QRO", "Iniciando...");
            return;
        }
    }
    Serial.printf("[AVISO] Pantalla LCD no detectada en SDA=GPIO%u, SCL=GPIO%u. "
                  "La estacion sigue funcionando sin ella.\n", PIN_SDA_LCD, PIN_SCL_LCD);
}

void mostrarMensajePantalla(const char* linea1, const char* linea2) {
    if (lcd == nullptr) {
        return;
    }
    escribirLinea(0, linea1);
    escribirLinea(1, linea2);
}

void actualizarPantalla(const Medicion& ultimaMuestra, const EstadoSistema& estado) {
    if (lcd == nullptr || millis() - ultimoCambioPagina < INTERVALO_PAGINA_LCD_MS) {
        return;
    }
    ultimoCambioPagina = millis();

    switch (paginaActual) {
        case 0: mostrarPaginaClima(ultimaMuestra); break;
        case 1: mostrarPaginaPresionLuz(ultimaMuestra); break;
        default: mostrarPaginaEstado(estado); break;
    }
    paginaActual = (paginaActual + 1) % NUM_PAGINAS;
}
