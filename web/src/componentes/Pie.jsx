// Pie de página: seguridad, privacidad, fuentes de datos y créditos.
import { URL_API, URL_REPOSITORIO } from '../configuracion'
import { IconoEscudo, IconoGithub } from './Iconos'

const ANIO_ACTUAL = new Date().getFullYear()

export default function Pie() {
  return (
    <footer className="pie">
      <div className="pie__contenido">
        <section>
          <h2><IconoEscudo /> Seguridad y privacidad</h2>
          <ul>
            <li>Toda la comunicación viaja cifrada por <strong>HTTPS</strong>, incluida la de la estación.</li>
            <li>La estación se identifica con un <strong>token</strong>; en la base solo se guarda su huella (hash).</li>
            <li>Cada lectura se <strong>valida</strong> antes de guardarse: se rechazan valores físicamente imposibles.</li>
            <li>Este sitio <strong>no usa cookies ni recopila datos personales</strong> de quien lo visita.</li>
          </ul>
        </section>
        <section>
          <h2>Fuentes de datos</h2>
          <ul>
            <li>Estación propia en el centro de Querétaro (ESP32).</li>
            <li>Histórico: reanálisis ERA5-Land (Copernicus / ECMWF).</li>
            <li>Modelo regional en tiempo real: <a href="https://open-meteo.com/" target="_blank" rel="noreferrer">Open-Meteo</a>.</li>
          </ul>
        </section>
        <section>
          <h2>Proyecto</h2>
          <ul>
            <li>
              <a href={URL_REPOSITORIO} target="_blank" rel="noreferrer" className="enlace-icono">
                <IconoGithub /> Código en GitHub
              </a>
            </li>
            <li><a href={`${URL_API}/docs`} target="_blank" rel="noreferrer">Documentación de la API</a></li>
            <li>Licencia MIT</li>
          </ul>
        </section>
      </div>
      <p className="pie__creditos">
        © {ANIO_ACTUAL} Monitoreo Microclimático de Querétaro · Proyecto académico
      </p>
    </footer>
  )
}
