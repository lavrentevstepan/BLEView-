#include <Arduino.h>
#include <WiFi.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>

#include <wificonfig.h>

const char* serverIP = "10.213.171.148";
const uint16_t serverPort = 8080;

#define GATEWAY_ID "4"
#define SCAN_TIME 5

const char* allowedMacs[] = { "48872d9cfb38", "48872d9cf51b" };
const int allowedMacsCount = sizeof(allowedMacs) / sizeof(allowedMacs[0]);


BLEScan* pBLEScan;
WiFiClient client;

unsigned long lastReconnectAttempt = 0;
const unsigned long reconnectInterval = 20000;

String formatMacAddress(BLEAddress address) {
  String mac = address.toString().c_str();
  mac.replace(":", "");
  return mac;
}


bool isAllowed(const String& mac, const String& name) {
  for (int i = 0; i < allowedMacsCount; i++) {
    if (mac == allowedMacs[i]) return true;
  }
  return false;
}

void connectToWiFi() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Connecting to WiFi...");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  }
}

void reconnectIfNeeded() {
  if (WiFi.status() != WL_CONNECTED) {
    unsigned long now = millis();
    if (now - lastReconnectAttempt > reconnectInterval) {
      lastReconnectAttempt = now;
      connectToWiFi();
    }
  }
}

class MyAdvertisedDeviceCallbacks : public BLEAdvertisedDeviceCallbacks {
  void onResult(BLEAdvertisedDevice advertisedDevice) {
    String mac = formatMacAddress(advertisedDevice.getAddress());
    String name = advertisedDevice.getName().c_str();
    int rssi = abs(advertisedDevice.getRSSI());

    if (isAllowed(mac, name)) {
      String output = GATEWAY_ID + String(",") + mac + String(",") + rssi;
      Serial.println(output);
      if (WiFi.status() == WL_CONNECTED && client.connected()) {
        client.println(output);
      }
    }
  }
};

void setup() {
  Serial.begin(115200);
  delay(2000);
  BLEDevice::init("BLE_Gateway");
  pBLEScan = BLEDevice::getScan(); 
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  pBLEScan->setInterval(100);
  pBLEScan->setWindow(99);
  pBLEScan->setActiveScan(true);

  connectToWiFi();
}

void loop() {
  reconnectIfNeeded();

  if (WiFi.status() == WL_CONNECTED && !client.connected()) {
    Serial.println("Connecting to server...");
    client.connect(serverIP, serverPort);
  }

  BLEScanResults foundDevices = pBLEScan->start(SCAN_TIME, false);
  pBLEScan->clearResults();
  delay(1000);
}
