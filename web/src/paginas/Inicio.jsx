// Inicio: consulta en tiempo real (lecturas y brecha térmica minuto a minuto).
import { obtenerBrecha, obtenerBrechaMinutos, obtenerEstacion, obtenerEstadoEstacion, obtenerLecturas } from '../api'
import { COLORES } from '../colores'
import { Alerta, Cargando, EstadoEstacion } from '../componentes/Estado'
import GraficoLineas from '../componentes/GraficoLineas'
import { IconoCiudad, IconoGota, IconoPresion, IconoSol, IconoTermometro } from '../componentes/Iconos'
import Panel from '../componentes/Panel'
import Tarjeta from '../componentes/Tarjeta'
import {
  ACTUALIZACION_TIEMPO_REAL_MS, CREDITO_FOTO, FOTO_PORTADA, HORAS_TIEMPO_REAL, MINUTOS_SIN_DATOS,
} from '../configuracion'
import { conSigno, diaHoraLocal, esAntigua, horaLocal, numero } from '../formato'
import useConsulta from '../useConsulta'

async function consultarTiempoReal() {
  // La API devuelve las últimas horas QUE TIENEN DATOS (terminan en la última lectura),
  // así que el Inicio nunca queda vacío aunque la estación esté detenida
  const [estacion, lecturas, minutos, horas, estadoRemoto] = await Promise.all([
    obtenerEstacion(),
    obtenerLecturas(HORAS_TIEMPO_REAL, HORAS_TIEMPO_REAL * 60),
    obtenerBrechaMinutos(HORAS_TIEMPO_REAL),
    obtenerBrecha(3),
    // El estado por MQTT es opcional: si falla, se usa solo la hora de la última lectura
    obtenerEstadoEstacion().catch(() => null),
  ])
  // Para las tarjetas se usa la temperatura del BME280 y, si falta, la del DHT11
  const ultima = lecturas.at(-1) ?? null
  const minutoConBrecha = [...minutos].reverse().find((fila) => fila.brecha_termica !== null) ?? null
  const horaConBrecha = [...horas].reverse().find((fila) => fila.presion_nivel_mar_sensor !== null) ?? null
  return {
    estacion,
    minutos,
    lecturas,
    ultima: ultima ? { ...ultima, temperatura: ultima.temperatura_bmp ?? ultima.temperatura_dht } : null,
    minutoConBrecha,
    horaConBrecha,
    // Si la última lectura es antigua, la estación está detenida y se muestra su último periodo con datos
    historico: ultima !== null && esAntigua(ultima.ts, MINUTOS_SIN_DATOS),
    estadoRemoto: estadoRemoto?.estado ?? null,
  }
}

export default function Inicio() {
  const { cargando, error, esperaLarga, datos, actualizadoEn } = useConsulta(
    consultarTiempoReal,
    ACTUALIZACION_TIEMPO_REAL_MS,
  )
  if (cargando) return <Cargando esperaLarga={esperaLarga} />

  const { estacion, minutos, lecturas, ultima, minutoConBrecha, horaConBrecha, historico, estadoRemoto } = datos ?? {
    minutos: [],
    lecturas: [],
    ultima: null,
    historico: false,
  }
  const brecha = minutoConBrecha?.brecha_termica ?? null
  const periodo = historico
    ? `Últimas ${HORAS_TIEMPO_REAL} horas registradas (hasta ${diaHoraLocal(ultima.ts)})`
    : `Últimas ${HORAS_TIEMPO_REAL} horas`

  return (
    <>
      <section className="portada" style={{ backgroundImage: `url(${FOTO_PORTADA})` }}>
        <div className="portada__contenido">
          <h1>{estacion?.nombre ?? 'Estación meteorológica'}</h1>
          <p className="portada__texto">
            Medimos minuto a minuto el clima de la calle para descubrir cuánto más caliente está el centro de
            Querétaro que la región que lo rodea.
          </p>
          <EstadoEstacion ultimaLectura={ultima} referencia={actualizadoEn} estadoRemoto={estadoRemoto} />
        </div>
        <p className="portada__credito">{CREDITO_FOTO}</p>
      </section>

      <Alerta error={error} />

      <section className="tarjetas" aria-label="Valores actuales">
        <Tarjeta
          destacada
          icono={<IconoCiudad />}
          titulo={historico ? 'Brecha térmica (último registro)' : 'Brecha térmica (ahora)'}
          valor={conSigno(brecha)}
          unidad=" °C"
          detalle={
            brecha === null
              ? 'Esperando la comparación con el modelo'
              : `${brecha >= 0 ? 'Calle más caliente' : 'Calle más fresca'} que la región · ${horaLocal(minutoConBrecha.ts)}`
          }
        />
        <Tarjeta
          icono={<IconoTermometro />}
          titulo="Temperatura"
          valor={numero(ultima?.temperatura)}
          unidad=" °C"
          detalle={ultima?.temperatura_dht != null ? `DHT11: ${numero(ultima.temperatura_dht)} °C` : null}
        />
        <Tarjeta icono={<IconoGota />} titulo="Humedad relativa" valor={numero(ultima?.humedad, 0)} unidad=" %" />
        <Tarjeta
          icono={<IconoPresion />}
          titulo="Presión"
          valor={numero(ultima?.presion_hpa)}
          unidad=" hPa"
          detalle={
            horaConBrecha?.presion_nivel_mar_sensor
              ? `${numero(horaConBrecha.presion_nivel_mar_sensor)} hPa a nivel del mar`
              : 'Medida en la estación'
          }
        />
        <Tarjeta icono={<IconoSol />} titulo="Luz" valor={numero(ultima?.iluminancia_lux, 0)} unidad=" lx" />
      </section>

      {lecturas.length === 0 ? (
        <Panel titulo="Aún no hay lecturas">
          <p className="vacio">La estación todavía no ha enviado datos. Aparecerán aquí en cuanto empiece a medir.</p>
        </Panel>
      ) : (
      <div className="rejilla-2">
        <Panel titulo="Temperatura minuto a minuto: calle vs. región" descripcion={periodo}>
          <GraficoLineas
            datos={minutos}
            claveX="ts"
            unidad="°C"
            altura={260}
            series={[
              { clave: 'temperatura_sensor', nombre: 'Sensor (calle)', color: COLORES.sensor },
              { clave: 'temperatura_modelo', nombre: 'Modelo regional', color: COLORES.modelo },
              { clave: 'temperatura_normal', nombre: 'Normal 2023–2025', color: COLORES.normal, punteada: true },
            ]}
          />
        </Panel>
        <Panel titulo="Humedad minuto a minuto: calle vs. región" descripcion={periodo}>
          <GraficoLineas
            datos={minutos}
            claveX="ts"
            unidad="%"
            altura={260}
            decimales={0}
            series={[
              { clave: 'humedad_sensor', nombre: 'Sensor (calle)', color: COLORES.sensor },
              { clave: 'humedad_modelo', nombre: 'Modelo regional', color: COLORES.modelo },
            ]}
          />
        </Panel>
      </div>
      )}
      <p className="nota">
        Se actualiza automáticamente cada 30 segundos. Cada punto del sensor es el promedio de 12 mediciones. El modelo
        regional y el normal histórico son datos por hora: entre una hora y la siguiente se interpolan linealmente.
      </p>
    </>
  )
}
