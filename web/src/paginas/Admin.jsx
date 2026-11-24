// Administración: inicio de sesión y control remoto de la estación (activar / detener).
import { useCallback, useEffect, useState } from 'react'
import {
  cerrarSesion, enviarComando, ErrorApi, iniciarSesion, obtenerEstadoEstacion,
  obtenerHistorialComandos, verificarSesion,
} from '../api'
import Panel from '../componentes/Panel'
import { diaHoraLocal } from '../formato'
import { borrarToken, guardarToken, leerToken } from '../sesion'

const INTERVALO_ESTADO_MS = 10_000

const ESTADOS = {
  midiendo: { texto: 'Midiendo', clase: 'activa', descripcion: 'La estación está tomando y enviando lecturas.' },
  en_espera: { texto: 'En espera', clase: 'espera', descripcion: 'Conectada y esperando la orden de activar.' },
  desconectado: { texto: 'Desconectada', clase: 'inactiva', descripcion: 'La estación perdió la conexión con el broker MQTT.' },
  desconocido: { texto: 'Sin información', clase: 'inactiva', descripcion: 'La estación aún no informó su estado.' },
}

function FormularioLogin({ alIniciar }) {
  const [usuario, setUsuario] = useState('')
  const [contrasena, setContrasena] = useState('')
  const [error, setError] = useState(null)
  const [enviando, setEnviando] = useState(false)

  async function enviar(evento) {
    evento.preventDefault()
    if (!usuario.trim() || !contrasena) {
      setError('Escriba el usuario y la contraseña.')
      return
    }
    setEnviando(true)
    setError(null)
    try {
      const sesion = await iniciarSesion(usuario.trim(), contrasena)
      guardarToken(sesion.token)
      alIniciar(sesion)
    } catch (e) {
      setError(e.message)
    } finally {
      setContrasena('') // la contraseña no se conserva en memoria
      setEnviando(false)
    }
  }

  return (
    <Panel titulo="Iniciar sesión" descripcion="Acceso solo para el equipo del proyecto.">
      <form className="formulario" onSubmit={enviar} noValidate>
        <label>
          Usuario
          <input value={usuario} onChange={(e) => { setUsuario(e.target.value); setError(null) }} autoComplete="username" />
        </label>
        <label>
          Contraseña
          <input type="password" value={contrasena} onChange={(e) => { setContrasena(e.target.value); setError(null) }} autoComplete="current-password" />
        </label>
        {error && <p className="formulario__error" role="alert">{error}</p>}
        <button className="boton boton--primario" type="submit" disabled={enviando}>
          {enviando ? 'Verificando…' : 'Entrar'}
        </button>
      </form>
    </Panel>
  )
}

function ControlEstacion({ sesion, alSalir }) {
  const [estado, setEstado] = useState(null)
  const [historial, setHistorial] = useState([])
  const [mensaje, setMensaje] = useState(null)
  const [enviando, setEnviando] = useState(false)

  // Si la sesión venció (401), se vuelve al formulario
  const manejarError = useCallback((e) => {
    if (e instanceof ErrorApi && e.codigo === 401) {
      borrarToken()
      alSalir('Su sesión expiró. Inicie sesión de nuevo.')
      return
    }
    setMensaje({ tipo: 'error', texto: e.message })
  }, [alSalir])

  const actualizar = useCallback(async () => {
    try {
      const [nuevoEstado, nuevoHistorial] = await Promise.all([obtenerEstadoEstacion(), obtenerHistorialComandos()])
      setEstado(nuevoEstado)
      setHistorial(nuevoHistorial)
    } catch (e) {
      manejarError(e)
    }
  }, [manejarError])

  useEffect(() => {
    actualizar()
    const intervalo = setInterval(actualizar, INTERVALO_ESTADO_MS)
    return () => clearInterval(intervalo)
  }, [actualizar])

  async function ordenar(accion) {
    setEnviando(true)
    setMensaje(null)
    try {
      await enviarComando(accion)
      setMensaje({
        tipo: 'exito',
        texto: accion === 'activar'
          ? 'Orden de activar enviada. La estación empieza a medir en unos segundos.'
          : 'Orden de detener enviada. La estación pasa a espera en unos segundos.',
      })
      setTimeout(actualizar, 3000)
    } catch (e) {
      manejarError(e)
    } finally {
      setEnviando(false)
    }
  }

  async function salir() {
    try {
      await cerrarSesion()
    } catch {
      // aunque falle, se borra la sesión local
    }
    borrarToken()
    alSalir(null)
  }

  const info = ESTADOS[estado?.estado] ?? ESTADOS.desconocido
  return (
    <>
      <Panel
        titulo="Control de la estación"
        descripcion={`Sesión de ${sesion.usuario} · expira ${diaHoraLocal(sesion.expira_en)}`}
        acciones={<button className="boton" onClick={salir}>Cerrar sesión</button>}
      >
        {estado && !estado.control_remoto ? (
          <p className="vacio">El control remoto no está configurado en la API (faltan las variables MQTT).</p>
        ) : (
          <div className="control">
            <div className={`estado estado--${info.clase}`} role="status">
              <span className="estado__punto" aria-hidden="true" />
              <div>
                <strong>{estado ? info.texto : 'Consultando…'}</strong>
                <span>{info.descripcion}</span>
              </div>
            </div>
            <div className="control__botones">
              <button className="boton boton--primario" disabled={enviando || estado?.estado === 'midiendo'} onClick={() => ordenar('activar')}>
                Activar medición
              </button>
              <button className="boton boton--peligro" disabled={enviando || estado?.estado === 'en_espera'} onClick={() => ordenar('detener')}>
                Detener
              </button>
            </div>
          </div>
        )}
        {mensaje && (
          <p className={mensaje.tipo === 'error' ? 'formulario__error' : 'formulario__exito'} role="status">
            {mensaje.texto}
          </p>
        )}
      </Panel>

      <Panel titulo="Últimas órdenes" descripcion="Registro de auditoría: quién activó o detuvo la estación.">
        {historial.length === 0 ? (
          <p className="vacio">Todavía no se envió ninguna orden.</p>
        ) : (
          <div className="tabla-contenedor">
            <table className="tabla">
              <thead>
                <tr><th>Fecha</th><th>Orden</th><th>Usuario</th></tr>
              </thead>
              <tbody>
                {historial.map((c) => (
                  <tr key={c.enviado_en}>
                    <td>{diaHoraLocal(c.enviado_en)}</td>
                    <td>{c.accion === 'activar' ? 'Activar' : 'Detener'}</td>
                    <td>{c.usuario ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </>
  )
}

export default function Admin() {
  const [sesion, setSesion] = useState(null)
  const [verificando, setVerificando] = useState(() => Boolean(leerToken()))
  const [aviso, setAviso] = useState(null)

  // Si hay un token guardado en esta pestaña, se comprueba que siga siendo válido
  useEffect(() => {
    if (!leerToken()) return
    verificarSesion()
      .then(setSesion)
      .catch(() => borrarToken())
      .finally(() => setVerificando(false))
  }, [])

  const alSalir = useCallback((textoAviso) => {
    setSesion(null)
    setAviso(textoAviso)
  }, [])

  return (
    <>
      <section className="encabezado-pagina">
        <div>
          <h1>Administración</h1>
          <p>Activa o detiene la estación a distancia. La orden viaja por MQTT hasta el ESP32.</p>
        </div>
      </section>
      {aviso && <p className="alerta" role="alert">{aviso}</p>}
      {verificando ? (
        <p className="vacio">Verificando sesión…</p>
      ) : sesion ? (
        <ControlEstacion sesion={sesion} alSalir={alSalir} />
      ) : (
        <FormularioLogin alIniciar={(s) => { setAviso(null); setSesion(s) }} />
      )}
    </>
  )
}
