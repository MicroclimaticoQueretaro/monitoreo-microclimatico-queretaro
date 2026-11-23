// Tarjeta con un valor actual (ej. temperatura), su unidad y un texto de apoyo.
export default function Tarjeta({ titulo, valor, unidad, detalle, icono, destacada = false }) {
  return (
    <article className={`tarjeta${destacada ? ' tarjeta--destacada' : ''}`}>
      <h3 className="tarjeta__titulo">
        {icono && <span className="tarjeta__icono" aria-hidden="true">{icono}</span>}
        {titulo}
      </h3>
      <p className="tarjeta__valor">
        {valor}
        {valor !== '—' && unidad && <span className="tarjeta__unidad">{unidad}</span>}
      </p>
      {detalle && <p className="tarjeta__detalle">{detalle}</p>}
    </article>
  )
}
