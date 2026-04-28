FROM ubuntu:22.04
RUN apt-get update && apt-get install -y \
    build-essential cmake git libssl-dev \
    libc-ares-dev uuid-dev libpaho-mqtt-dev libpaho-mqttpp-dev
COPY . /app
WORKDIR /app
RUN g++ main.cpp -o mqtt_cpp -lpaho-mqttpp3 -lpaho-mqtt3as
CMD ["./mqtt_cpp"]