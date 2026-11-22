"""Pruebas unitarias de los cálculos meteorológicos (no necesitan base de datos)."""

import pytest

from app.calculos import diferencia, presion_a_nivel_del_mar, radiacion_estimada_desde_lux


def test_presion_al_nivel_del_mar_no_cambia_a_altitud_cero():
    assert presion_a_nivel_del_mar(1013.2, 0, 15) == 1013.2


def test_presion_de_queretaro_reducida_queda_cerca_de_1013():
    # ~823.5 hPa medidos a ~1820 m equivalen a una presión normal a nivel del mar
    reducida = presion_a_nivel_del_mar(823.5, 1820, 24)
    assert reducida == pytest.approx(1011, abs=3)


def test_presion_reducida_aumenta_con_la_altitud():
    assert presion_a_nivel_del_mar(823.5, 2000, 20) > presion_a_nivel_del_mar(823.5, 1800, 20)


@pytest.mark.parametrize("datos", [(None, 1820, 20), (823.5, None, 20), (823.5, 1820, None)])
def test_presion_sin_datos_devuelve_none(datos):
    assert presion_a_nivel_del_mar(*datos) is None


def test_radiacion_estimada_desde_lux():
    assert radiacion_estimada_desde_lux(60000) == 500.0
    assert radiacion_estimada_desde_lux(None) is None


def test_diferencia():
    assert diferencia(24.6, 21.1) == 3.5
    assert diferencia(None, 21.1) is None
    assert diferencia(24.6, None) is None
