# Usamos una versión de Python oficial
FROM python:3.10-slim

# Instalamos las dependencias del sistema necesarias para dlib y face_recognition
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libx11-dev \
    libatlas-base-dev \
    libboost-python-dev \
    libboost-thread-dev \
    && rm -rf /var/lib/apt/lists/*

# Definimos el directorio de trabajo
WORKDIR /app

# Copiamos el archivo de requerimientos
COPY requirements.txt .

# Instalamos las librerías de Python (esto tardará unos minutos la primera vez)
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el contenido del proyecto
COPY . .

# Comando para ejecutar la app (Render usa el puerto 10000 por defecto)
CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "10000"]