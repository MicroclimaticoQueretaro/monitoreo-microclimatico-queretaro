// Contenedor con título y descripción para cada gráfico.
export default function Panel({ titulo, descripcion, children }) {
  return (
    <section className="panel">
      <header className="panel__encabezado">
        <h2>{titulo}</h2>
        {descripcion && <p>{descripcion}</p>}
      </header>
      {children}
    </section>
  )
}
