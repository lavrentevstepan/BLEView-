#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <map>

#define GATEWAY_ID "1"
#define SCAN_TIME 5

std::vector<String> allowedMacs = {
  "48872d9cfb38",
};

BLEScan* pBLEScan;

String formatMacAddress(BLEAddress address) {
  String raw = address.toString().c_str();
  raw.toLowerCase();
  raw.replace(":", "");
  return raw;
}

bool isAllowed(String mac, String name) {
  for (String allowed : allowedMacs) {
    if (mac == allowed) return true;
  }
  return false;
}

class MyAdvertisedDeviceCallbacks : public BLEAdvertisedDeviceCallbacks {
  void onResult(BLEAdvertisedDevice advertisedDevice) {
    String mac = formatMacAddress(advertisedDevice.getAddress());
    String name = advertisedDevice.getName().c_str();
    int rssi = abs(advertisedDevice.getRSSI());

    if (isAllowed(mac, name)) {
      Serial.printf("%s,%s,%d\n", GATEWAY_ID, mac.c_str(), rssi);
    }
  }
};

void setup() {
  Serial.begin(115200);
  Serial.println("BLE Gateway Started");

  BLEDevice::init("BLE_Gateway");
  pBLEScan = BLEDevice::getScan(); 
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  pBLEScan->setInterval(100);
  pBLEScan->setWindow(99);
  pBLEScan->setActiveScan(true); 
}

void loop() {
  BLEScanResults foundDevices = pBLEScan->start(SCAN_TIME, false);
  pBLEScan->clearResults();
  delay(1000);
}
