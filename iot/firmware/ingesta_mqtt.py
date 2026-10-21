import paho.mqtt.client as mqtt
import json

# Configuración del broker y tema (ajustar según tu arquitectura)
BROKER = "test.mosquitto.org"  # Cambiar por la IP de tu broker si usas uno local
PORT = 1883
TOPIC = "monitoreo/queretaro/esp32/clima"

# Función que se ejecuta al conectar con el broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Conectado exitosamente al broker MQTT. Suscrito a: {TOPIC}")
        client.subscribe(TOPIC)
    else:
        print(f"Fallo en la conexión. Código de error: {rc}")

# Función que se ejecuta cada vez que el ESP32 envía un dato
def on_message(client, userdata, msg):
    try:
        # Decodificar el mensaje JSON que llega por WiFi
        payload = msg.payload.decode('utf-8')
        datos_clima = json.loads(payload)

        print("=== Nueva lectura recibida del ESP32 ===")
        print(f"Temperatura: {datos_clima.get('temperatura')} °C")
        print(f"Humedad: {datos_clima.get('humedad')} %")
        print("-" * 30)

        # El siguiente paso será guardar estos datos_clima en la base de datos

    except json.JSONDecodeError:
        print("Error: El mensaje recibido no es un JSON válido.")

# Configuración del cliente MQTT
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# Conexión y bucle de escucha infinita
print("Iniciando conexión con el broker...")
client.connect(BROKER, PORT, 60)
client.loop_forever()
