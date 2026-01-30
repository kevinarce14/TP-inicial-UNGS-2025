FROM python:3.10-slim

# Evita que Python genere archivos .pyc y que el output se guarde en buffer
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instalación de dependencias con re-intento y limpieza
RUN apt-get update --fix-missing && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libx11-dev \
    libatlas-base-dev \
    libboost-python-dev \
    libboost-thread-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Primero instalamos dlib por separado (es lo que más tarda y falla)
# Esto ayuda a que si falla lo demás, dlib ya esté en caché
RUN pip install --no-cache-dir dlib==19.24.1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Usamos el puerto 10000 que es el estándar de Render
CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "10000"]