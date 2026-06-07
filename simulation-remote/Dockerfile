FROM python:3.10-slim

# Instala apenas as dependências gráficas fundamentais do Linux
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglapi-mesa \
    libosmesa6 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala a versão leve de CPU do PyTorch e as dependências do ecossistema
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir pygame paho-mqtt pyzmq ultralytics opencv-python-headless

COPY . .

# Dispara o script principal do Pygame diretamente
CMD ["python", "-u", "main.py"]