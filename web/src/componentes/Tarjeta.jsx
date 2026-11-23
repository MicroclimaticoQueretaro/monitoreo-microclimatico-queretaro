// Tarjeta con un valor actual (ej. temperatura) y un texto de apoyo.
export default function Tarjeta({ titulo, valor, unidad, detalle, destacada = false }) {
  return (
    <article className={`tarjeta${destacada ? ' tarjeta--destacada' : ''}`}>
      <h3 className="tarjeta__titulo">{titulo}</h3>
      <p className="tarjeta__valor">
        {valor}
        {valor !== '—' && unidad && <span className="tarjeta__unidad">{unidad}</span>}
      </p>
      {detalle && <p className="tarjeta__detalle">{detalle}</p>}
    </article>
  )
}
