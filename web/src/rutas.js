// Navegación simple entre secciones usando el "hash" de la URL (#/inicio, #/graficos...).
// Con hash no hace falta configurar el servidor: funciona igual en local y en la nube.
import { useEffect, useState } from 'react'

// "oculta": la sección existe (se abre escribiendo #/admin en la dirección) pero no aparece en el menú.
// Ocultarla solo evita distracciones: la protección real es el inicio de sesión de la API.
export const SECCIONES = [
  { ruta: 'inicio', nombre: 'Inicio' },
  { ruta: 'graficos', nombre: 'Gráficos' },
  { ruta: 'sobre', nombre: 'Sobre' },
  { ruta: 'admin', nombre: 'Admin', oculta: true },
]

function leerRuta() {
  const ruta = window.location.hash.replace(/^#\/?/, '')
  return SECCIONES.some((s) => s.ruta === ruta) ? ruta : 'inicio'
}

export function useRuta() {
  const [ruta, setRuta] = useState(leerRuta)
  useEffect(() => {
    const alCambiar = () => {
      setRuta(leerRuta())
      window.scrollTo({ top: 0 })
    }
    window.addEventListener('hashchange', alCambiar)
    return () => window.removeEventListener('hashchange', alCambiar)
  }, [])
  return ruta
}
