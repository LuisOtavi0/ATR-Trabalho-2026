import paho.mqtt.client as mqtt
import time

broker = "mqtt-broker"

def on_connect(client, userdata, flags, rc):
    print(f"Python conectado com código {rc}")
    client.subscribe("topico/teste")

def on_message(client, userdata, msg):
    print(f"Python recebeu: {msg.payload.decode()} no tópico {msg.topic}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(broker, 1883, 60)
client.loop_start()

while True:
    client.publish("topico/teste", "Mensagem vinda do Python!")
    time.sleep(5)