// Vista en tabla de los mismos datos de los gráficos (accesibilidad y consulta exacta).
import { conSigno, diaHoraLocal, numero } from '../formato'

export default function TablaHoras({ datos }) {
  const filas = [...datos].reverse() // la hora más reciente primero
  return (
    <div className="tabla-contenedor">
      <table className="tabla">
        <thead>
          <tr>
            <th>Hora</th>
            <th>Lecturas</th>
            <th>Sensor (°C)</th>
            <th>Modelo (°C)</th>
            <th>Normal (°C)</th>
            <th>Brecha (°C)</th>
            <th>Humedad sensor (%)</th>
            <th>Humedad modelo (%)</th>
            <th>Presión nivel del mar (hPa)</th>
          </tr>
        </thead>
        <tbody>
          {filas.map((fila) => (
            <tr key={fila.hora}>
              <td>{diaHoraLocal(fila.hora)}</td>
              <td>{fila.lecturas_promediadas}</td>
              <td>{numero(fila.temperatura_sensor)}</td>
              <td>{numero(fila.temperatura_modelo)}</td>
              <td>{numero(fila.temperatura_normal)}</td>
              <td>{conSigno(fila.brecha_termica)}</td>
              <td>{numero(fila.humedad_sensor)}</td>
              <td>{numero(fila.humedad_modelo)}</td>
              <td>{numero(fila.presion_nivel_mar_sensor)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
