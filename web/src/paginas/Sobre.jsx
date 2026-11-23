// Sobre el proyecto: propósito, funcionamiento, metodología y equipo.
import { IconoGithub } from '../componentes/Iconos'
import Panel from '../componentes/Panel'
import { EQUIPO } from '../datos/equipo'

const CAPAS = [
  {
    titulo: 'Hardware',
    texto: 'Un ESP32 con sensores de temperatura, humedad, presión y luz mide cada 5 segundos y envía el promedio de cada minuto por WiFi.',
    detalle: 'ESP32 · BME280 · DHT11 · BH1750 · LCD',
  },
  {
    titulo: 'API y datos',
    texto: 'Una API recibe las lecturas, las valida y las guarda en una base de datos de series de tiempo, junto con el histórico y el modelo regional.',
    detalle: 'FastAPI · PostgreSQL · TimescaleDB · Docker',
  },
  {
    titulo: 'Web',
    texto: 'Este sitio consulta la API y muestra en tiempo real lo que pasa en la calle y cómo se compara con la región.',
    detalle: 'React · Vite · Recharts',
  },
]

// Iniciales: primer nombre + primer apellido (en nombres hispanos, el penúltimo)
function iniciales(nombre) {
  const partes = nombre.split(' ')
  const primerApellido = partes.length >= 3 ? partes[partes.length - 2] : partes.at(-1)
  return (partes[0][0] + primerApellido[0]).toUpperCase()
}

function TarjetaPersona({ persona }) {
  return (
    <article className="persona">
      {persona.foto ? (
        <img className="persona__foto" src={persona.foto} alt={`Foto de ${persona.nombre}`} loading="lazy" />
      ) : (
        <div className="persona__foto persona__foto--iniciales" aria-hidden="true">
          {iniciales(persona.nombre)}
        </div>
      )}
      <h3>{persona.nombre}</h3>
      <p className="persona__carrera">{persona.carrera}</p>
      <p className="persona__institucion">{persona.institucion}</p>
      {persona.github && (
        <a className="enlace-icono" href={`https://github.com/${persona.github}`} target="_blank" rel="noreferrer">
          <IconoGithub /> {persona.github}
        </a>
      )}
    </article>
  )
}

export default function Sobre() {
  return (
    <>
      <section className="encabezado-pagina">
        <div>
          <h1>Sobre el proyecto</h1>
          <p>Una estación meteorológica de bajo costo para medir la isla de calor urbana en Querétaro.</p>
        </div>
      </section>

      <Panel titulo="¿Por qué este proyecto?">
        <div className="texto">
          <p>
            Las ciudades suelen estar más calientes que su entorno: el asfalto y los edificios acumulan calor y
            la falta de vegetación reduce el enfriamiento. A este fenómeno se le llama <strong>isla de calor
            urbana</strong> y afecta la salud, el consumo de energía y la calidad de vida.
          </p>
          <p>
            Los datos climáticos disponibles (satélites y modelos) representan áreas de varios kilómetros, por lo
            que no captan lo que ocurre en una calle concreta. Este proyecto instala un sensor en el centro de
            Querétaro y compara sus mediciones con el clima de la región para responder una pregunta:
            <strong> ¿cuántos grados más caliente está el centro que su entorno?</strong>
          </p>
        </div>
      </Panel>

      <Panel titulo="¿Cómo funciona?" descripcion="El sistema tiene tres capas.">
        <div className="capas">
          {CAPAS.map((capa, i) => (
            <article key={capa.titulo} className="capa">
              <span className="capa__numero" aria-hidden="true">{i + 1}</span>
              <h3>{capa.titulo}</h3>
              <p>{capa.texto}</p>
              <p className="capa__detalle">{capa.detalle}</p>
            </article>
          ))}
        </div>
      </Panel>

      <Panel titulo="Metodología">
        <dl className="definiciones">
          <div>
            <dt>Brecha térmica</dt>
            <dd>
              Temperatura del sensor menos la del modelo regional (Open-Meteo) en la misma hora. El modelo se ajusta a
              la altitud de la estación para que la diferencia no se deba a la altura. Un valor positivo indica que la
              calle está más caliente que la región.
            </dd>
          </div>
          <div>
            <dt>Normal histórico</dt>
            <dd>
              Promedio del reanálisis ERA5-Land de 2023 a 2025 para el mismo mes y hora. Indica si hoy está más caliente
              de lo habitual para la época.
            </dd>
          </div>
          <div>
            <dt>Presión a nivel del mar</dt>
            <dd>La presión medida se reduce al nivel del mar con la fórmula barométrica para compararla con el modelo.</dd>
          </div>
          <div>
            <dt>Limitaciones</dt>
            <dd>
              Precisión del sensor de ±1 °C (BME280) y ±2 °C (DHT11). El sensor de luz mide lux, no radiación solar: la
              radiación se estima de forma aproximada. Una sola estación no representa a toda la ciudad.
            </dd>
          </div>
        </dl>
      </Panel>

      <Panel titulo="Equipo">
        <div className="equipo">
          {EQUIPO.map((persona) => (
            <TarjetaPersona key={persona.nombre} persona={persona} />
          ))}
        </div>
      </Panel>
    </>
  )
}
