"""Cálculos meteorológicos usados en la comparación sensor vs. modelo.

Son funciones "puras" (no usan la base de datos), por eso se prueban fácilmente.
Todas devuelven None si falta algún dato, en lugar de fallar.
"""

GRADIENTE_TERMICO = 0.0065      # °C por metro: la temperatura baja ~0.65 °C cada 100 m
EXPONENTE_BAROMETRICO = 5.257   # g·M / (R·gradiente) de la atmósfera estándar
KELVIN = 273.15

# Aproximación para luz solar: 1 W/m² ≈ 120 lux.
# Solo es razonable con sol directo; con nubes o sombra el error es grande.
FACTOR_LUX_A_WM2 = 120.0


def presion_a_nivel_del_mar(
    presion_hpa: float | None, altitud_m: float | None, temperatura_c: float | None
) -> float | None:
    """Reduce la presión medida en la estación al nivel del mar (fórmula barométrica).

    La presión de la estación depende casi solo de la altitud (~823 hPa en Querétaro).
    Reducida al nivel del mar (~1013 hPa) se puede comparar con cualquier otro lugar
    y con la presión a nivel del mar que entrega el modelo.
    """
    if presion_hpa is None or altitud_m is None or temperatura_c is None:
        return None
    correccion = GRADIENTE_TERMICO * altitud_m
    factor = 1 - correccion / (temperatura_c + correccion + KELVIN)
    return round(presion_hpa * factor ** (-EXPONENTE_BAROMETRICO), 1)


def radiacion_estimada_desde_lux(iluminancia_lux: float | None) -> float | None:
    """Estimación APROXIMADA de radiación solar (W/m²) a partir de la iluminancia (lux)."""
    if iluminancia_lux is None:
        return None
    return round(iluminancia_lux / FACTOR_LUX_A_WM2, 1)


def diferencia(valor_sensor: float | None, valor_referencia: float | None) -> float | None:
    """Sensor menos referencia, redondeado a 2 decimales. None si falta alguno."""
    if valor_sensor is None or valor_referencia is None:
        return None
    return round(valor_sensor - valor_referencia, 2)
