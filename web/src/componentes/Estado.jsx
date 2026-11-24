// Mensajes de carga, error y estado de la estación.
import { MINUTOS_SIN_DATOS } from '../configuracion'
import { haceCuanto } from '../formato'

export function Cargando({ esperaLarga }) {
  return (
    <div className="cargando" role="status">
      <div className="cargando__circulo" aria-hidden="true" />
      <p>Cargando datos de la estación…</p>
      {esperaLarga && (
        <p className="cargando__aviso">
          El servidor gratuito se estaba durmiendo y puede tardar cerca de 1 minuto en despertar.
        </p>
      )}
    </div>
  )
}

export function Alerta({ error }) {
  if (!error) return null
  return (
    <p className="alerta" role="alert">
      No se pudo actualizar: {error}. Se muestran los últimos datos disponibles.
    </p>
  )
}

// estadoRemoto: lo que informa la estación por MQTT ("midiendo", "en_espera", "desconectado")
export function EstadoEstacion({ ultimaLectura, referencia, estadoRemoto }) {
  const minutos =
    ultimaLectura && referencia
      ? (referencia.getTime() - new Date(ultimaLectura.ts).getTime()) / 60_000
      : Infinity
  const textoLectura = ultimaLectura
    ? `Última lectura ${haceCuanto(ultimaLectura.ts, referencia)}`
    : 'Aún no hay lecturas'

  let clase = minutos <= MINUTOS_SIN_DATOS ? 'activa' : 'inactiva'
  let titulo = minutos <= MINUTOS_SIN_DATOS ? 'Estación midiendo' : 'Sin datos recientes'
  if (estadoRemoto === 'en_espera') {
    clase = 'espera'
    titulo = 'Estación en espera'
  } else if (estadoRemoto === 'desconectado') {
    clase = 'inactiva'
    titulo = 'Estación desconectada'
  }

  return (
    <div className={`estado estado--${clase}`} role="status">
      <span className="estado__punto" aria-hidden="true" />
      <div>
        <strong>{titulo}</strong>
        <span>{textoLectura}</span>
      </div>
    </div>
  )
}
