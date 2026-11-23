// Funciones para consultar la API. Cada una devuelve los datos ya convertidos de JSON.
import { CODIGO_ESTACION, URL_API } from './configuracion'

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

export async function obtenerEstacion() {
  const estaciones = await pedir('/api/v1/estaciones')
  return estaciones.find((e) => e.codigo === CODIGO_ESTACION) ?? null
}

// Lecturas minuto a minuto, de la más antigua a la más reciente
export async function obtenerLecturas(horas, limite = 1000) {
  const lecturas = await pedir(`/api/v1/estaciones/${estacion}/lecturas?horas=${horas}&limite=${limite}`)
  return [...lecturas].reverse()
}

// Comparación por hora con el modelo y el normal histórico, de la más antigua a la más reciente
export async function obtenerBrecha(horas) {
  const filas = await pedir(`/api/v1/estaciones/${estacion}/brecha?horas=${horas}`)
  return [...filas].reverse()
}
