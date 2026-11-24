// Funciones para consultar la API. Cada una devuelve los datos ya convertidos de JSON.
import { CODIGO_ESTACION, URL_API } from './configuracion'
import { leerToken } from './sesion'

// En el plan gratuito de la nube, la API "se duerme" tras 15 min sin uso y tarda
// cerca de 1 minuto en despertar: por eso el tiempo de espera es largo.
const TIEMPO_ESPERA_MS = 90_000

// Error con el código HTTP, para distinguir por ejemplo 401 (sesión vencida)
export class ErrorApi extends Error {
  constructor(mensaje, codigo) {
    super(mensaje)
    this.codigo = codigo
  }
}

async function pedir(ruta, { metodo = 'GET', cuerpo, autenticado = false } = {}) {
  const controlador = new AbortController()
  const temporizador = setTimeout(() => controlador.abort(), TIEMPO_ESPERA_MS)
  const cabeceras = {}
  if (cuerpo !== undefined) cabeceras['Content-Type'] = 'application/json'
  if (autenticado) cabeceras.Authorization = `Bearer ${leerToken()}`
  try {
    const respuesta = await fetch(`${URL_API}${ruta}`, {
      method: metodo,
      headers: cabeceras,
      body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined,
      signal: controlador.signal,
    })
    if (!respuesta.ok) {
      // La API explica el error en el campo "detail"
      const detalle = await respuesta.json().then((d) => d.detail).catch(() => null)
      const mensaje = typeof detalle === 'string' ? detalle : `La API respondió con el código ${respuesta.status}`
      throw new ErrorApi(mensaje, respuesta.status)
    }
    return respuesta.status === 204 ? null : await respuesta.json()
  } finally {
    clearTimeout(temporizador)
  }
}

const estacion = encodeURIComponent(CODIGO_ESTACION)

// --- Consultas públicas ---

export async function obtenerEstacion() {
  const estaciones = await pedir('/api/v1/estaciones')
  return estaciones.find((e) => e.codigo === CODIGO_ESTACION) ?? null
}

// Las consultas devuelven las N horas que TERMINAN EN LA ÚLTIMA LECTURA de la estación:
// si la estación está detenida, se muestran sus datos más recientes en lugar de nada.

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

// Comparación minuto a minuto (modelo y normal interpolados entre horas), de la más antigua a la más reciente
export async function obtenerBrechaMinutos(horas) {
  const filas = await pedir(`/api/v1/estaciones/${estacion}/brecha/minutos?horas=${horas}`)
  return [...filas].reverse()
}

// Estado que informa la propia estación por MQTT (midiendo, en_espera, desconectado)
export const obtenerEstadoEstacion = () => pedir(`/api/v1/estaciones/${estacion}/estado`)

// --- Administración (requieren sesión) ---

export const iniciarSesion = (usuario, contrasena) =>
  pedir('/api/v1/admin/login', { metodo: 'POST', cuerpo: { usuario, contrasena } })

export const verificarSesion = () => pedir('/api/v1/admin/sesion', { autenticado: true })

export const cerrarSesion = () => pedir('/api/v1/admin/logout', { metodo: 'POST', autenticado: true })

export const enviarComando = (accion) =>
  pedir(`/api/v1/estaciones/${estacion}/comando`, { metodo: 'POST', cuerpo: { accion }, autenticado: true })

export const obtenerHistorialComandos = () =>
  pedir(`/api/v1/estaciones/${estacion}/comandos?limite=10`, { autenticado: true })
