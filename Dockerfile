FROM python:3.10-slim

# Cambiamos a los mirrors de debian para evitar el error 100
RUN sed -i 's/deb.debian.org/archive.debian.org/g' /etc/apt/sources.list && \
    sed -i 's|security.debian.org/debian-security|archive.debian.org/debian-security|g' /etc/apt/sources.list && \
    sed -i '/stretch-updates/d' /etc/apt/sources.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libx11-dev \
    libatlas-base-dev \
    libboost-python-dev \
    libboost-thread-dev \
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