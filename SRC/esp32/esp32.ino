#include <WiFi.h>
#include <PubSubClient.h>
#include "DHT.h"
#include "config.h"

#define DHTPIN 4
#define DHTTYPE DHT11

WiFiClient wclient;
PubSubClient mqttClient(wclient);
DHT dht(DHTPIN, DHTTYPE);

unsigned long lastSend = 0;
const long interval = 60000;

String uuid;

void connectWifi(){
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Conectando ao WiFi");
  while(WiFi.status() != WL_CONNECTED){
    delay(500);
    Serial.print(".");
  }

  // Pega o MAC e remove os ':'
  uuid = WiFi.macAddress();
  uuid.replace(":", "");

  Serial.println("\nConectado ao WiFi, UUID: " + uuid);
}

void connectMqtt(){
  while (!mqttClient.connected()){
    String clientId = "raintrack-" + uuid;
    if (mqttClient.connect(clientId.c_str())){
      Serial.println("Conectado ao MQTT");
    } else {
      Serial.println("Tentando MQTT de novo em 5s...");
      delay(5000);
    }
  }
}

void setup(){
  Serial.begin(115200);
  dht.begin();
  connectWifi();
  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
}

void loop(){
  if (!mqttClient.connected()){
    connectMqtt();
  }
  mqttClient.loop();

  unsigned long now = millis();
  if (now - lastSend >= interval){
    lastSend = now;

    float h = dht.readHumidity();
    float t = dht.readTemperature();

    if (isnan(h) || isnan(t)) {
      Serial.println("Erro ao ler DHT11");
      return;
    }

    char msg[150];
    snprintf(msg, sizeof(msg),
             "{\"uuid\": \"%s\", \"TEMPERATURA\": %.2f, \"HUMIDADE\": %.2f}",
             uuid.c_str(), t, h);

    Serial.print("Enviando: ");
    Serial.println(msg);

    mqttClient.publish(MQTT_TOPIC, msg);
  }
}
