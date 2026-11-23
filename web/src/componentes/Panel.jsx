// Contenedor con título y descripción para cada gráfico o bloque de contenido.
export default function Panel({ titulo, descripcion, acciones, children }) {
  return (
    <section className="panel">
      {(titulo || acciones) && (
        <header className="panel__encabezado">
          <div>
            {titulo && <h2>{titulo}</h2>}
            {descripcion && <p>{descripcion}</p>}
          </div>
          {acciones}
        </header>
      )}
      {children}
    </section>
  )
}
