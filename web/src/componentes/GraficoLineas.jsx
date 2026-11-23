// Gráfico de líneas para comparar series en el tiempo.
import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { diaHoraLocal, horaLocal, numero } from '../formato'

const estiloEje = { fill: 'var(--texto-secundario)', fontSize: 12 }

// series: [{ clave, nombre, color, punteada }]
// claveX: campo con la fecha ("hora" para datos por hora, "ts" para lecturas por minuto)
// formatoEje: cómo se escribe la fecha en el eje (hora por defecto; día para periodos largos)
export default function GraficoLineas({ datos, series, unidad, claveX = 'hora', altura = 300, decimales = 1, formatoEje = horaLocal }) {
  const variasSeries = series.length > 1
  return (
    <ResponsiveContainer width="100%" height={altura}>
      <LineChart data={datos} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--linea-grilla)" vertical={false} />
        <XAxis dataKey={claveX} tickFormatter={formatoEje} minTickGap={40} tick={estiloEje} stroke="var(--linea-eje)" />
        <YAxis unit={unidad} width={64} domain={['auto', 'auto']} tick={estiloEje} stroke="var(--linea-eje)" />
        <Tooltip
          labelFormatter={diaHoraLocal}
          formatter={(valor, nombre) => [`${numero(valor, decimales)} ${unidad}`, nombre]}
          contentStyle={{ background: '#fff', border: '1px solid var(--borde)', borderRadius: 8 }}
        />
        {/* La leyenda solo hace falta con 2+ series; con una, el título del panel ya la nombra */}
        {variasSeries && (
          <Legend
            itemSorter={null}
            wrapperStyle={{ fontSize: 13 }}
            formatter={(nombre) => <span style={{ color: 'var(--texto-secundario)' }}>{nombre}</span>}
          />
        )}
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
            activeDot={{ r: 5, strokeWidth: 2, stroke: '#fff' }}
            connectNulls={false}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
