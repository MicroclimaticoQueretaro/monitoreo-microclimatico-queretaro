# Etapa 1: compilar el proyecto React con Node
FROM node:22-alpine AS compilacion
WORKDIR /app
# Primero las dependencias (aprovecha la caché de Docker si solo cambia el código)
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Dirección de la API que usará la página (se fija al compilar)
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# Etapa 2: servir los archivos compilados con nginx (imagen final pequeña, sin Node)
FROM nginx:1.27-alpine
COPY --from=compilacion /app/dist /usr/share/nginx/html
EXPOSE 80
