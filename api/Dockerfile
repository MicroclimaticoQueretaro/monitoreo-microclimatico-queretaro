# Imagen ligera de Python
FROM python:3.12-slim

# No generar archivos .pyc y mostrar los logs al instante
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Se copian primero las dependencias para aprovechar la caché de Docker:
# si solo cambia el código, no se reinstala todo
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts

# Seguridad: la API corre con un usuario sin privilegios, no como root
RUN useradd --create-home --shell /usr/sbin/nologin api
USER api

EXPOSE 8000
# El puerto se lee de la variable PORT (la define Render en la nube); en local usa 8000.
# --proxy-headers: detrás del proxy HTTPS de la nube, respeta el protocolo y la IP originales.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
