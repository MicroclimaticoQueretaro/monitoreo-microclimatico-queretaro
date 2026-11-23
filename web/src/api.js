// Funciones para consultar la API. Cada una devuelve los datos ya convertidos de JSON.
import { CODIGO_ESTACION, HORAS_GRAFICOS, URL_API } from './configuracion'

// En el plan gratuito de la nube, la API "se duerme" tras 15 min sin uso y tarda
// cerca de 1 minuto en despertar: por eso el tiempo de espera es largo.
const TIEMPO_ESPERA_MS = 90_000

async function pedir(ruta) {
  const controlador = new AbortController()
  const temporizador = setTimeout(() => controlador.abort(), TIEMPO_ESPERA_MS)
  try {
    const respuesta = await fetch(`${URL_API}${ruta}`, { signal: controlador.signal })
    if (!respuesta.ok) {
      throw new Error(`La API respondió con el código ${respuesta.status}`)
    }
    return await respuesta.json()
  } finally {
    clearTimeout(temporizador)
  }
}

const estacion = encodeURIComponent(CODIGO_ESTACION)

export const obtenerEstaciones = () => pedir('/api/v1/estaciones')

export const obtenerUltimaLectura = async () => {
  const lecturas = await pedir(`/api/v1/estaciones/${estacion}/lecturas?horas=24&limite=1`)
  return lecturas[0] ?? null
}

// La API devuelve las horas de la más reciente a la más antigua; los gráficos las necesitan al revés
export const obtenerBrecha = async () => {
  const horas = await pedir(`/api/v1/estaciones/${estacion}/brecha?horas=${HORAS_GRAFICOS}`)
  return [...horas].reverse()
}
