// Gráficos: comparación por hora entre la calle, el modelo regional y el normal histórico.
import { useState } from 'react'
import { obtenerBrecha } from '../api'
import { COLORES } from '../colores'
import { Alerta, Cargando } from '../componentes/Estado'
import GraficoBrecha from '../componentes/GraficoBrecha'
import GraficoLineas from '../componentes/GraficoLineas'
import Panel from '../componentes/Panel'
import TablaHoras from '../componentes/TablaHoras'
import { ACTUALIZACION_GRAFICOS_MS } from '../configuracion'
import { diaHoraLocal, diaLocal, esAntigua, horaLocal } from '../formato'
import useConsulta from '../useConsulta'

const PERIODOS = [
  { horas: 24, nombre: '24 h' },
  { horas: 48, nombre: '48 h' },
  { horas: 168, nombre: '7 días' },
]

function SelectorPeriodo({ horas, alCambiar }) {
  return (
    <div className="selector" role="group" aria-label="Periodo">
      {PERIODOS.map((p) => (
        <button
          key={p.horas}
          className={`selector__opcion${p.horas === horas ? ' selector__opcion--activa' : ''}`}
          aria-pressed={p.horas === horas}
          onClick={() => alCambiar(p.horas)}
        >
          {p.nombre}
        </button>
      ))}
    </div>
  )
}

export default function Graficos() {
  const [horas, setHoras] = useState(48)
  const { cargando, error, esperaLarga, datos } = useConsulta(
    () => obtenerBrecha(horas),
    ACTUALIZACION_GRAFICOS_MS,
    [horas],
  )
  const filas = datos ?? []
  // Los periodos terminan en la última lectura: si es antigua, se indica hasta cuándo hay datos
  const ultimaHora = filas.at(-1)?.hora ?? null
  const avisoPeriodo =
    ultimaHora && esAntigua(ultimaHora, 90) ? `Mostrando los datos registrados hasta ${diaHoraLocal(ultimaHora)}.` : null
  // Para 7 días, el eje muestra la fecha; para 24/48 h, la hora
  const formatoEje = horas > 48 ? diaLocal : horaLocal

  return (
    <>
      <section className="encabezado-pagina">
        <div>
          <h1>Gráficos</h1>
          <p>Promedios por hora: la calle (sensor) frente a la región (modelo) y a lo normal para la época.</p>
        </div>
        <SelectorPeriodo horas={horas} alCambiar={setHoras} />
      </section>

      <Alerta error={error} />
      {avisoPeriodo && <p className="nota nota--aviso">{avisoPeriodo}</p>}
      {cargando ? (
        <Cargando esperaLarga={esperaLarga} />
      ) : (
        <>
          <Panel
            titulo="Temperatura: calle vs. región vs. lo normal"
            descripcion="El modelo regional está ajustado a la altitud de la estación. El normal es el promedio 2023–2025 para ese mes y hora."
          >
            <GraficoLineas
              formatoEje={formatoEje}
              datos={filas}
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
            <GraficoBrecha datos={filas} formatoEje={formatoEje} />
          </Panel>

          <Panel titulo="Humedad relativa" descripcion="Sensor vs. modelo regional.">
            <GraficoLineas
              formatoEje={formatoEje}
              datos={filas}
              unidad="%"
              decimales={0}
              series={[
                { clave: 'humedad_sensor', nombre: 'Sensor (calle)', color: COLORES.sensor },
                { clave: 'humedad_modelo', nombre: 'Modelo regional', color: COLORES.modelo },
              ]}
            />
          </Panel>

          <Panel titulo="Datos en tabla" descripcion="Los mismos valores de los gráficos, hora por hora.">
            <TablaHoras datos={filas} />
          </Panel>
        </>
      )}
    </>
  )
}
