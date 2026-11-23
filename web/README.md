# Dashboard — Monitoreo Microclimático

Página web en **React + Vite** con gráficos de **Recharts**. Consulta la API y se actualiza cada minuto.

## Secciones

| Sección | Contenido |
|---|---|
| **Inicio** (`#/inicio`) | Tiempo real: estado de la estación, valores actuales, brecha térmica y gráficos minuto a minuto de las últimas 3 h. Se actualiza cada 30 s |
| **Gráficos** (`#/graficos`) | Comparación por hora (24 h, 48 h o 7 días): calle vs. modelo regional vs. normal histórico, brecha térmica, humedad y tabla |
| **Sobre el proyecto** (`#/sobre`) | Propósito, funcionamiento en tres capas, metodología y equipo |

Pie de página con seguridad, privacidad, fuentes de datos y enlaces. Diseño claro (blanco, verde y celeste), adaptado a celular.

## Estructura

```
web/src/
├── App.jsx              # Cabecera + sección actual + pie
├── rutas.js             # Navegación entre secciones (#/inicio, #/graficos, #/sobre)
├── useConsulta.js       # Consulta a la API que se repite cada cierto tiempo
├── api.js               # Consultas a la API
├── configuracion.js     # URL de la API, estación e intervalos
├── formato.js           # Fechas en hora de Querétaro y formato de números
├── colores.js           # Colores de las series de los gráficos
├── datos/equipo.js      # Integrantes (para agregar fotos: web/public/equipo/)
├── paginas/             # Inicio, Graficos, Sobre
└── componentes/         # Cabecera, Pie, Tarjeta, Panel, gráficos, tabla, íconos
```

## Desarrollo

```bash
cd web
npm install
npm run dev        # http://localhost:5173 (con la API corriendo en localhost:8000)
npm run build      # compila a la carpeta dist/
```

La dirección de la API se configura con `VITE_API_URL` (ver `.env.example`).
Las variables `VITE_` quedan visibles en el navegador: **nunca** poner secretos ahí.
