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

export function EstadoEstacion({ ultimaLectura, referencia }) {
  const minutos =
    ultimaLectura && referencia
      ? (referencia.getTime() - new Date(ultimaLectura.ts).getTime()) / 60_000
      : Infinity
  const activa = minutos <= MINUTOS_SIN_DATOS
  return (
    <div className={`estado ${activa ? 'estado--activa' : 'estado--inactiva'}`} role="status">
      <span className="estado__punto" aria-hidden="true" />
      <div>
        <strong>{activa ? 'Estación midiendo' : 'Sin datos recientes'}</strong>
        <span>
          {ultimaLectura ? `Última lectura ${haceCuanto(ultimaLectura.ts, referencia)}` : 'Aún no hay lecturas'}
        </span>
      </div>
    </div>
  )
}
