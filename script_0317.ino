#include "DHT.h"

#define DHTPIN 4
#define DHTTYPE DHT22
#define SOIL_PIN 34

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);
  dht.begin();
  Serial.println("Sensor Test Starting...");
}

void loop() {
  float temp = dht.readTemperature();
  float humidity = dht.readHumidity();
  int soilRaw = analogRead(SOIL_PIN);

  //float soilMoisture = map(soilRaw, 0, 4095, 0, 100); use this if you want raw soilMoisture without the set range
  float soilMoisture = map(soilRaw, 2000, 3300, 100, 0); //range has been set, 0% is dry(air), 100% is wet(in water) 
  soilMoisture = constrain(soilMoisture, 0, 100);

  if (isnan(temp) || isnan(humidity)) {
    Serial.println("DHT22 read failed!");
  } else {
    Serial.print("Temp: ");
    Serial.print(temp);
    Serial.print(" °C | Humidity: ");
    Serial.print(humidity);
    Serial.print(" %");
  }

  Serial.print(" | Soil: ");
  Serial.print(soilMoisture);
  Serial.println(" %");

  delay(2000);
}