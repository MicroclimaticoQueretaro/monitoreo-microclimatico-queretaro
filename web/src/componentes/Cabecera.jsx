// Cabecera fija con el nombre del proyecto y el menú de secciones.
import { SECCIONES } from '../rutas'

export default function Cabecera({ rutaActual }) {
  return (
    <header className="cabecera">
      <div className="cabecera__contenido">
        <a href="#/inicio" className="marca" aria-label="Ir al inicio">
          <svg className="marca__logo" viewBox="0 0 32 32" aria-hidden="true">
            {/* Cielo celeste, sol y termómetro */}
            <circle cx="16" cy="16" r="15.5" fill="#bae6fd" />
            <circle cx="10" cy="11" r="5" fill="#f59e0b" />
            <rect x="17.5" y="5" width="7" height="17" rx="3.5" fill="#fff" stroke="#c2410c" strokeWidth="1.5" />
            <circle cx="21" cy="23.5" r="5" fill="#ea580c" stroke="#c2410c" strokeWidth="1.5" />
            <rect x="19.6" y="11" width="2.8" height="12" rx="1.4" fill="#ea580c" />
            <path d="M24.5 9h-2M24.5 13h-2M24.5 17h-2" stroke="#c2410c" strokeWidth="1" strokeLinecap="round" />
          </svg>
          <span>
            <strong>Microclima Querétaro</strong>
            <small>Monitoreo de la isla de calor urbana</small>
          </span>
        </a>
        <nav aria-label="Secciones">
          <ul className="menu">
            {SECCIONES.filter((seccion) => !seccion.oculta).map((seccion) => (
              <li key={seccion.ruta}>
                <a
                  href={`#/${seccion.ruta}`}
                  className={`menu__enlace${rutaActual === seccion.ruta ? ' menu__enlace--activo' : ''}`}
                  aria-current={rutaActual === seccion.ruta ? 'page' : undefined}
                >
                  {seccion.nombre}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </header>
  )
}
