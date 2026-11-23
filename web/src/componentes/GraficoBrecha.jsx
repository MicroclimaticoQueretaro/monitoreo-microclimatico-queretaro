// Barras de la brecha térmica por hora: naranja = calle más caliente, azul = más fresca.
import {
  Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { COLORES } from '../colores'
import { conSigno, diaHoraLocal, horaLocal } from '../formato'

export default function GraficoBrecha({ datos }) {
  const conDato = datos.filter((fila) => fila.brecha_termica !== null)
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={conDato} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--linea-grilla)" vertical={false} />
        <XAxis
          dataKey="hora"
          tickFormatter={horaLocal}
          minTickGap={40}
          tick={{ fill: 'var(--texto-secundario)', fontSize: 12 }}
          stroke="var(--linea-eje)"
        />
        <YAxis
          unit=" °C"
          width={60}
          tick={{ fill: 'var(--texto-secundario)', fontSize: 12 }}
          stroke="var(--linea-eje)"
        />
        <ReferenceLine y={0} stroke="var(--texto-secundario)" />
        <Tooltip
          labelFormatter={diaHoraLocal}
          formatter={(valor) => [`${conSigno(valor)} °C`, 'Brecha térmica']}
          contentStyle={{ background: 'var(--superficie)', border: '1px solid var(--borde)', borderRadius: 8 }}
          cursor={{ fill: 'var(--linea-grilla)' }}
        />
        <Bar dataKey="brecha_termica" radius={[4, 4, 0, 0]} isAnimationActive={false}>
          {conDato.map((fila) => (
            <Cell key={fila.hora} fill={fila.brecha_termica >= 0 ? COLORES.calor : COLORES.frio} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
