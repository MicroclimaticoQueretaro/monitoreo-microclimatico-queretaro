// Gráfico de líneas para comparar series en el tiempo (sensor, modelo, normal histórico).
import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { diaHoraLocal, horaLocal, numero } from '../formato'

// series: [{ clave, nombre, color, punteada }]
export default function GraficoLineas({ datos, series, unidad }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={datos} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--linea-grilla)" vertical={false} />
        <XAxis
          dataKey="hora"
          tickFormatter={horaLocal}
          minTickGap={40}
          tick={{ fill: 'var(--texto-secundario)', fontSize: 12 }}
          stroke="var(--linea-eje)"
        />
        <YAxis
          unit={unidad}
          width={60}
          domain={['auto', 'auto']}
          tick={{ fill: 'var(--texto-secundario)', fontSize: 12 }}
          stroke="var(--linea-eje)"
        />
        <Tooltip
          labelFormatter={diaHoraLocal}
          formatter={(valor, nombre) => [`${numero(valor)} ${unidad}`, nombre]}
          contentStyle={{ background: 'var(--superficie)', border: '1px solid var(--borde)', borderRadius: 8 }}
        />
        {/* Leyenda en el mismo orden que las series; el texto usa el color de texto, no el de la serie */}
        <Legend
          itemSorter={null}
          wrapperStyle={{ fontSize: 13 }}
          formatter={(nombre) => <span style={{ color: 'var(--texto-secundario)' }}>{nombre}</span>}
        />
        {series.map((serie) => (
          <Line
            key={serie.clave}
            type="monotone"
            dataKey={serie.clave}
            name={serie.nombre}
            stroke={serie.color}
            strokeWidth={2}
            strokeDasharray={serie.punteada ? '6 4' : undefined}
            dot={false}
            activeDot={{ r: 5, strokeWidth: 2, stroke: 'var(--superficie)' }}
            connectNulls={false}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
