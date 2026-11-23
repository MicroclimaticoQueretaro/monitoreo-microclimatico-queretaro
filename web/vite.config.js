import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Configuración de Vite (herramienta que compila el proyecto React)
export default defineConfig({
  plugins: [react()],
  build: {
    // La biblioteca de gráficos (Recharts) es grande; el aviso de 500 kB no aplica aquí
    chunkSizeWarningLimit: 900,
  },
})
