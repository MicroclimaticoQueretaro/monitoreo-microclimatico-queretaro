// Hook que carga los datos de la API y los actualiza cada minuto.
import { useCallback, useEffect, useState } from 'react'
import { obtenerBrecha, obtenerEstaciones, obtenerUltimaLectura } from './api'
import { CODIGO_ESTACION, INTERVALO_ACTUALIZACION_MS } from './configuracion'

export default function useDatos() {
  const [estado, setEstado] = useState({
    cargando: true,
    error: null,
    estacion: null,
    ultimaLectura: null,
    horas: [],
    actualizadoEn: null,
  })
  // Si la primera carga tarda, se avisa que el servidor gratuito puede estar "despertando"
  const [esperaLarga, setEsperaLarga] = useState(false)

  const cargar = useCallback(async () => {
    try {
      // Las tres consultas se hacen en paralelo
      const [estaciones, ultimaLectura, horas] = await Promise.all([
        obtenerEstaciones(),
        obtenerUltimaLectura(),
        obtenerBrecha(),
      ])
      setEstado({
        cargando: false,
        error: null,
        estacion: estaciones.find((e) => e.codigo === CODIGO_ESTACION) ?? null,
        ultimaLectura,
        horas,
        actualizadoEn: new Date(),
      })
    } catch (error) {
      // Se conservan los últimos datos buenos y solo se muestra el error
      setEstado((anterior) => ({ ...anterior, cargando: false, error: error.message }))
    } finally {
      setEsperaLarga(false)
    }
  }, [])

  useEffect(() => {
    const aviso = setTimeout(() => setEsperaLarga(true), 5000)
    cargar().finally(() => clearTimeout(aviso))
    const intervalo = setInterval(cargar, INTERVALO_ACTUALIZACION_MS)
    return () => {
      clearTimeout(aviso)
      clearInterval(intervalo)
    }
  }, [cargar])

  return { ...estado, esperaLarga }
}
