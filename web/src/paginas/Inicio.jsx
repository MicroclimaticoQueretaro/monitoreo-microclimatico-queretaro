// Inicio: consulta en tiempo real (lecturas minuto a minuto de la estación).
import { obtenerBrecha, obtenerEstacion, obtenerEstadoEstacion, obtenerLecturas } from '../api'
import { COLORES } from '../colores'
import { Alerta, Cargando, EstadoEstacion } from '../componentes/Estado'
import GraficoLineas from '../componentes/GraficoLineas'
import { IconoCiudad, IconoGota, IconoPresion, IconoSol, IconoTermometro } from '../componentes/Iconos'
import Panel from '../componentes/Panel'
import Tarjeta from '../componentes/Tarjeta'
import { ACTUALIZACION_TIEMPO_REAL_MS, CREDITO_FOTO, FOTO_PORTADA, HORAS_TIEMPO_REAL } from '../configuracion'
import { conSigno, diaHoraLocal, numero } from '../formato'
import useConsulta from '../useConsulta'

async function consultarTiempoReal() {
  const [estacion, lecturas, horas, estadoRemoto] = await Promise.all([
    obtenerEstacion(),
    obtenerLecturas(HORAS_TIEMPO_REAL, HORAS_TIEMPO_REAL * 60),
    obtenerBrecha(24),
    // El estado por MQTT es opcional: si falla, se usa solo la hora de la última lectura
    obtenerEstadoEstacion().catch(() => null),
  ])
  // Si la estación no envió nada en las últimas horas, se busca su última lectura (hasta 30 días atrás)
  const ultimaDisponible = lecturas.length > 0 ? lecturas.at(-1) : (await obtenerLecturas(24 * 30, 1)).at(-1) ?? null
  // Para los gráficos se usa la temperatura del BME280 y, si falta, la del DHT11
  const conTemperatura = (l) => ({ ...l, temperatura: l.temperatura_bmp ?? l.temperatura_dht })
  const horaConBrecha = [...horas].reverse().find((fila) => fila.brecha_termica !== null) ?? null
  return {
    estacion,
    lecturas: lecturas.map(conTemperatura),
    ultima: ultimaDisponible ? conTemperatura(ultimaDisponible) : null,
    horaConBrecha,
    estadoRemoto: estadoRemoto?.estado ?? null,
  }
}

export default function Inicio() {
  const { cargando, error, esperaLarga, datos, actualizadoEn } = useConsulta(
    consultarTiempoReal,
    ACTUALIZACION_TIEMPO_REAL_MS,
  )
  if (cargando) return <Cargando esperaLarga={esperaLarga} />

  const { estacion, lecturas, ultima, horaConBrecha, estadoRemoto } = datos ?? { lecturas: [], ultima: null }
  const brecha = horaConBrecha?.brecha_termica ?? null

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
          titulo="Brecha térmica (última hora)"
          valor={conSigno(brecha)}
          unidad=" °C"
          detalle={
            brecha === null
              ? 'Esperando la comparación con el modelo'
              : brecha >= 0
                ? 'La calle está más caliente que la región'
                : 'La calle está más fresca que la región'
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
        <Panel titulo="Sin lecturas recientes">
          <p className="vacio">
            La estación no envió datos en las últimas {HORAS_TIEMPO_REAL} horas
            {ultima ? `. Arriba se muestra su última lectura (${diaHoraLocal(ultima.ts)}).` : '.'} Los registros
            anteriores están disponibles en la sección <a href="#/graficos">Gráficos</a>.
          </p>
        </Panel>
      ) : (
      <div className="rejilla-2">
        <Panel titulo="Temperatura minuto a minuto" descripcion={`Últimas ${HORAS_TIEMPO_REAL} horas`}>
          <GraficoLineas
            datos={lecturas}
            claveX="ts"
            unidad="°C"
            altura={240}
            series={[{ clave: 'temperatura', nombre: 'Temperatura', color: COLORES.sensor }]}
          />
        </Panel>
        <Panel titulo="Humedad minuto a minuto" descripcion={`Últimas ${HORAS_TIEMPO_REAL} horas`}>
          <GraficoLineas
            datos={lecturas}
            claveX="ts"
            unidad="%"
            altura={240}
            decimales={0}
            series={[{ clave: 'humedad', nombre: 'Humedad', color: COLORES.humedad }]}
          />
        </Panel>
      </div>
      )}
      <p className="nota">Se actualiza automáticamente cada 30 segundos. Cada punto es el promedio de 12 mediciones.</p>
    </>
  )
}
