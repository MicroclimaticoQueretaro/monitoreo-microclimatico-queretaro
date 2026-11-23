// Hook genérico: ejecuta una consulta a la API y la repite cada cierto tiempo.
// Conserva los últimos datos buenos si una actualización falla.
import { useCallback, useEffect, useRef, useState } from 'react'

export default function useConsulta(consultar, intervaloMs, dependencias = []) {
  const [estado, setEstado] = useState({ cargando: true, error: null, datos: null, actualizadoEn: null })
  const [esperaLarga, setEsperaLarga] = useState(false)
  const consultaRef = useRef(consultar)
  consultaRef.current = consultar

  const cargar = useCallback(async () => {
    try {
      const datos = await consultaRef.current()
      setEstado({ cargando: false, error: null, datos, actualizadoEn: new Date() })
    } catch (error) {
      setEstado((anterior) => ({ ...anterior, cargando: false, error: error.message }))
    } finally {
      setEsperaLarga(false)
    }
  }, [])

  useEffect(() => {
    // Si la primera carga tarda, se avisa que el servidor gratuito puede estar "despertando"
    const aviso = setTimeout(() => setEsperaLarga(true), 5000)
    cargar().finally(() => clearTimeout(aviso))
    const intervalo = setInterval(cargar, intervaloMs)
    return () => {
      clearTimeout(aviso)
      clearInterval(intervalo)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cargar, intervaloMs, ...dependencias])

  return { ...estado, esperaLarga }
}
