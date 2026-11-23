// Dashboard del Monitoreo Microclimático de Querétaro.
import { useState } from 'react'
import { COLORES } from './colores'
import GraficoBrecha from './componentes/GraficoBrecha'
import GraficoLineas from './componentes/GraficoLineas'
import Panel from './componentes/Panel'
import TablaHoras from './componentes/TablaHoras'
import Tarjeta from './componentes/Tarjeta'
import { HORAS_GRAFICOS, URL_API } from './configuracion'
import { conSigno, haceCuanto, numero } from './formato'
import useDatos from './useDatos'

const MINUTOS_SIN_DATOS = 5 // si la última lectura es más antigua, la estación se muestra inactiva

// Última hora que ya tiene comparación con el modelo
function ultimaHoraConBrecha(horas) {
  return [...horas].reverse().find((fila) => fila.brecha_termica !== null) ?? null
}

function Encabezado({ estacion, ultimaLectura, actualizadoEn }) {
  // Se compara con el momento de la última actualización (no con Date.now) para que el render sea puro
  const minutos =
    ultimaLectura && actualizadoEn
      ? (actualizadoEn.getTime() - new Date(ultimaLectura.ts).getTime()) / 60_000
      : Infinity
  const activa = minutos <= MINUTOS_SIN_DATOS
  return (
    <header className="encabezado">
      <div>
        <p className="encabezado__antetitulo">Monitoreo microclimático · Querétaro</p>
        <h1>{estacion?.nombre ?? 'Estación meteorológica'}</h1>
        {estacion && (
          <p className="encabezado__detalle">
            {estacion.codigo} · {numero(estacion.latitud, 4)}, {numero(estacion.longitud, 4)} ·{' '}
            {numero(estacion.altitud_m, 0)} m s. n. m.
          </p>
        )}
      </div>
      <div className={`estado ${activa ? 'estado--activa' : 'estado--inactiva'}`} role="status">
        <span className="estado__punto" aria-hidden="true" />
        <div>
          <strong>{activa ? 'Estación en línea' : 'Sin datos recientes'}</strong>
          <span>
            {ultimaLectura ? `Última lectura ${haceCuanto(ultimaLectura.ts, actualizadoEn)}` : 'Aún no hay lecturas'}
            {actualizadoEn && ' · se actualiza cada minuto'}
          </span>
        </div>
      </div>
    </header>
  )
}

function Tarjetas({ ultimaLectura, horaBrecha }) {
  const l = ultimaLectura ?? {}
  const temperatura = l.temperatura_bmp ?? l.temperatura_dht
  const brecha = horaBrecha?.brecha_termica ?? null
  const textoBrecha =
    brecha === null
      ? 'Esperando datos del modelo'
      : brecha >= 0
        ? 'La calle está más caliente que la región'
        : 'La calle está más fresca que la región'
  return (
    <section className="tarjetas" aria-label="Valores actuales">
      <Tarjeta
        destacada
        titulo="Brecha térmica (última hora)"
        valor={conSigno(brecha)}
        unidad=" °C"
        detalle={textoBrecha}
      />
      <Tarjeta titulo="Temperatura" valor={numero(temperatura)} unidad=" °C" detalle="Sensor BME280" />
      <Tarjeta titulo="Humedad relativa" valor={numero(l.humedad, 0)} unidad=" %" />
      <Tarjeta
        titulo="Presión"
        valor={numero(l.presion_hpa)}
        unidad=" hPa"
        detalle={
          horaBrecha?.presion_nivel_mar_sensor
            ? `${numero(horaBrecha.presion_nivel_mar_sensor)} hPa a nivel del mar`
            : 'En la estación'
        }
      />
      <Tarjeta titulo="Iluminancia" valor={numero(l.iluminancia_lux, 0)} unidad=" lx" />
    </section>
  )
}

export default function App() {
  const { cargando, error, esperaLarga, estacion, ultimaLectura, horas, actualizadoEn } = useDatos()
  const [verTabla, setVerTabla] = useState(false)

  if (cargando) {
    return (
      <main className="pagina pagina--centrada">
        <div className="cargando" role="status">
          <div className="cargando__circulo" aria-hidden="true" />
          <p>Cargando datos de la estación…</p>
          {esperaLarga && (
            <p className="cargando__aviso">
              El servidor gratuito se estaba durmiendo y puede tardar cerca de 1 minuto en despertar.
            </p>
          )}
        </div>
      </main>
    )
  }

  return (
    <main className="pagina">
      <Encabezado estacion={estacion} ultimaLectura={ultimaLectura} actualizadoEn={actualizadoEn} />

      {error && (
        <p className="alerta" role="alert">
          No se pudo actualizar: {error}. Se muestran los últimos datos disponibles.
        </p>
      )}

      <Tarjetas ultimaLectura={ultimaLectura} horaBrecha={ultimaHoraConBrecha(horas)} />

      <Panel
        titulo="Temperatura: calle vs. región vs. lo normal"
        descripcion={`Promedio por hora de las últimas ${HORAS_GRAFICOS} h. El modelo está ajustado a la altitud de la estación.`}
      >
        <GraficoLineas
          datos={horas}
          unidad="°C"
          series={[
            { clave: 'temperatura_sensor', nombre: 'Sensor (calle)', color: COLORES.sensor },
            { clave: 'temperatura_modelo', nombre: 'Modelo regional', color: COLORES.modelo },
            { clave: 'temperatura_normal', nombre: 'Normal 2023–2025', color: COLORES.normal, punteada: true },
          ]}
        />
      </Panel>

      <Panel
        titulo="Brecha térmica por hora"
        descripcion="Sensor menos modelo. Barras naranjas: la calle está más caliente que la región (isla de calor)."
      >
        <GraficoBrecha datos={horas} />
      </Panel>

      <Panel titulo="Humedad relativa" descripcion="Sensor vs. modelo regional, promedio por hora.">
        <GraficoLineas
          datos={horas}
          unidad="%"
          series={[
            { clave: 'humedad_sensor', nombre: 'Sensor (calle)', color: COLORES.sensor },
            { clave: 'humedad_modelo', nombre: 'Modelo regional', color: COLORES.modelo },
          ]}
        />
      </Panel>

      <section className="panel">
        <button className="boton" onClick={() => setVerTabla((v) => !v)} aria-expanded={verTabla}>
          {verTabla ? 'Ocultar tabla' : 'Ver datos en tabla'}
        </button>
        {verTabla && <TablaHoras datos={horas} />}
      </section>

      <footer className="pie">
        <h2>Metodología</h2>
        <ul>
          <li>
            <strong>Sensor:</strong> ESP32 con BME280, DHT11 y BH1750; una lectura por minuto (promedio de 12
            muestras).
          </li>
          <li>
            <strong>Modelo regional:</strong> Open-Meteo, ajustado a la altitud de la estación. La diferencia
            sensor − modelo es la brecha térmica.
          </li>
          <li>
            <strong>Normal histórico:</strong> promedio del reanálisis ERA5-Land (2023–2025) para el mismo mes y
            hora.
          </li>
          <li>
            <strong>Limitaciones:</strong> precisión del sensor ±1 °C; la radiación se estima a partir de lux
            (aproximación).
          </li>
        </ul>
        <p>
          <a href={`${URL_API}/docs`} target="_blank" rel="noreferrer">Documentación de la API</a>
        </p>
      </footer>
    </main>
  )
}
