// Guarda el token de la sesión de administrador.
// Se usa sessionStorage (no localStorage): el token se borra al cerrar la pestaña,
// así una sesión olvidada en una computadora compartida no queda abierta.
const CLAVE = 'microclima_sesion_admin'

export function leerToken() {
  try {
    return sessionStorage.getItem(CLAVE)
  } catch {
    return null
  }
}

export function guardarToken(token) {
  try {
    sessionStorage.setItem(CLAVE, token)
  } catch {
    // Navegadores con almacenamiento bloqueado: la sesión dura solo mientras la página esté abierta
  }
}

export function borrarToken() {
  try {
    sessionStorage.removeItem(CLAVE)
  } catch {
    // nada que borrar
  }
}
