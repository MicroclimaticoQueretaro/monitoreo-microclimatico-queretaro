// Funciones de formato: fechas en hora de Querétaro y números con unidades.
import { ZONA_HORARIA } from './configuracion'

const formatoHora = new Intl.DateTimeFormat('es-MX', {
  timeZone: ZONA_HORARIA, hour: '2-digit', minute: '2-digit', hour12: false,
})
const formatoDiaHora = new Intl.DateTimeFormat('es-MX', {
  timeZone: ZONA_HORARIA, day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false,
})

export const horaLocal = (fecha) => formatoHora.format(new Date(fecha))
export const diaHoraLocal = (fecha) => formatoDiaHora.format(new Date(fecha))

// Número con decimales fijos, o "—" si no hay dato
export const numero = (valor, decimales = 1) =>
  valor === null || valor === undefined || Number.isNaN(valor) ? '—' : Number(valor).toFixed(decimales)

// Con signo explícito (+2.1 / −0.8): útil para diferencias
export const conSigno = (valor, decimales = 1) => {
  if (valor === null || valor === undefined) return '—'
  const texto = Math.abs(valor).toFixed(decimales)
  return valor > 0 ? `+${texto}` : valor < 0 ? `−${texto}` : texto
}

// "hace 3 min", "hace 2 h"
export const haceCuanto = (fecha, referencia = new Date()) => {
  const minutos = Math.round((referencia.getTime() - new Date(fecha).getTime()) / 60_000)
  if (minutos < 1) return 'hace menos de 1 min'
  if (minutos < 60) return `hace ${minutos} min`
  return `hace ${Math.round(minutos / 60)} h`
}
