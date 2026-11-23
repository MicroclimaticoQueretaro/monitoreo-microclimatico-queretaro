// Configuración del dashboard.
// VITE_API_URL se define al compilar (en la nube apunta a la API pública).
// Las variables VITE_ quedan visibles en el navegador: NUNCA poner secretos aquí.
export const URL_API = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')
export const CODIGO_ESTACION = import.meta.env.VITE_CODIGO_ESTACION ?? 'QRO-CENTRO-01'
export const URL_REPOSITORIO = 'https://github.com/marialuisaas/monitoreo-microclimatico-queretaro'
export const ZONA_HORARIA = 'America/Mexico_City'

// Foto de portada (Inicio). Para cambiarla, reemplazar el archivo en web/public/imagenes/
// y actualizar el crédito. Usar solo fotos propias o con licencia libre.
export const FOTO_PORTADA = '/imagenes/centro-queretaro.jpg'
export const CREDITO_FOTO = 'Foto: equipo del proyecto'

// Inicio: tiempo real (el ESP32 envía una lectura por minuto)
export const HORAS_TIEMPO_REAL = 3
export const ACTUALIZACION_TIEMPO_REAL_MS = 30_000
// Gráficos: comparación por hora
export const ACTUALIZACION_GRAFICOS_MS = 120_000
export const MINUTOS_SIN_DATOS = 5 // si la última lectura es más antigua, la estación se muestra inactiva
