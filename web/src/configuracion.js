// Configuración del dashboard.
// VITE_API_URL se define al compilar (en la nube apunta a la API pública).
// Las variables VITE_ quedan visibles en el navegador: NUNCA poner secretos aquí.
export const URL_API = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')
export const CODIGO_ESTACION = import.meta.env.VITE_CODIGO_ESTACION ?? 'QRO-CENTRO-01'
export const HORAS_GRAFICOS = 48
export const INTERVALO_ACTUALIZACION_MS = 60_000 // el ESP32 envía una lectura por minuto
export const ZONA_HORARIA = 'America/Mexico_City'
