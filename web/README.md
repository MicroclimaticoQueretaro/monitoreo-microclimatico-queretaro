# Dashboard — Monitoreo Microclimático

Página web en **React + Vite** con gráficos de **Recharts**. Consulta la API y se actualiza cada minuto.

## Qué muestra

- **Tarjetas** con los valores actuales y la **brecha térmica** de la última hora.
- **Temperatura:** sensor (calle) vs. modelo regional vs. normal histórico 2023–2025.
- **Brecha térmica por hora:** sensor menos modelo (naranja = calle más caliente).
- **Humedad:** sensor vs. modelo.
- **Tabla** con los mismos datos, para consulta exacta y accesibilidad.

Funciona en tema claro y oscuro (según el sistema) y en celular.

## Estructura

```
web/src/
├── App.jsx              # Página principal: encabezado, tarjetas y paneles
├── useDatos.js          # Carga los datos de la API y los actualiza cada minuto
├── api.js               # Consultas a la API
├── configuracion.js     # URL de la API, estación y tiempos
├── formato.js           # Fechas en hora de Querétaro y formato de números
├── colores.js           # Colores de las series
└── componentes/         # Tarjeta, Panel, gráficos y tabla
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
