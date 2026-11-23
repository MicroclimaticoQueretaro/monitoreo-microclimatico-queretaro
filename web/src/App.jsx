// Estructura general del sitio: cabecera con menú, sección actual y pie de página.
import Cabecera from './componentes/Cabecera'
import Pie from './componentes/Pie'
import Graficos from './paginas/Graficos'
import Inicio from './paginas/Inicio'
import Sobre from './paginas/Sobre'
import { useRuta } from './rutas'

const PAGINAS = { inicio: Inicio, graficos: Graficos, sobre: Sobre }

export default function App() {
  const ruta = useRuta()
  const Pagina = PAGINAS[ruta]
  return (
    <>
      {/* Enlace para teclado/lectores de pantalla (no usa el hash para no cambiar de sección) */}
      <a
        className="saltar"
        href="#/"
        onClick={(evento) => {
          evento.preventDefault()
          document.getElementById('contenido')?.focus()
        }}
      >
        Saltar al contenido
      </a>
      <Cabecera rutaActual={ruta} />
      <main id="contenido" className="pagina" tabIndex={-1}>
        <Pagina />
      </main>
      <Pie />
    </>
  )
}
