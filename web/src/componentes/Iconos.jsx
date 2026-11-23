// Íconos simples en SVG (sin bibliotecas externas). Heredan el color del texto.
const base = { width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round' }

export const IconoTermometro = () => (
  <svg {...base}><path d="M14 14.8V5a2 2 0 1 0-4 0v9.8a4 4 0 1 0 4 0Z" /><path d="M12 9v7" /></svg>
)
export const IconoGota = () => (
  <svg {...base}><path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11Z" /></svg>
)
export const IconoPresion = () => (
  <svg {...base}><circle cx="12" cy="12" r="8" /><path d="M12 12l4-3" /><path d="M8 16h8" /></svg>
)
export const IconoSol = () => (
  <svg {...base}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>
)
export const IconoCiudad = () => (
  <svg {...base}><path d="M3 21h18M5 21V9l5-3v15M10 21V4l9 4v13" /><path d="M14 11h2M14 15h2" /></svg>
)
export const IconoEscudo = () => (
  <svg {...base}><path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6l8-3Z" /><path d="M9 12l2 2 4-4" /></svg>
)
export const IconoGithub = () => (
  <svg {...base}><path d="M9 19c-4 1.5-4-2-6-2.5M15 21v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2 4.2 4.2 0 0 0-.1-3.2s-1.1-.3-3.5 1.3a12.3 12.3 0 0 0-6.2 0C6.5 2.8 5.4 3.1 5.4 3.1a4.2 4.2 0 0 0-.1 3.2A4.6 4.6 0 0 0 4 9.5c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V21" /></svg>
)
