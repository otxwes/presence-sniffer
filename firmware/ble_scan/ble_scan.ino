/*
 * ble_scan — ESP32-S3 passive BLE advertisement scanner (board 2 / BLE).
 *
 * Observes BLE advertisements only. The scan is PASSIVE (setActiveScan(false)):
 * no scan requests are sent, so the board never transmits — receive-only,
 * the same posture as wifi_probe.
 *
 * One JSON line per unique advertiser per ~1 s scan window:
 *
 *   {"ts_ms":12345,"mac":"aa:bb:cc:dd:ee:ff","rssi":-79,"name":"iPhone"}
 *   {"ts_ms":12345,"mac":"11:22:33:44:55:66","rssi":-95,"name":null}
 *
 * Passive scan receives no scan-response payloads, so names appear only when
 * the advertiser fits them into the primary advertising packet. A heartbeat
 * every ~5 s:
 *
 *   {"hb":5001,"adverts":123}
 *
 * Event lines are dropped when the USB TX buffer is nearly full so a slow or
 * absent reader can never stall the sniffer (same guard as wifi_probe).
 *
 * Build + flash: see README.md in this directory.
 */
#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>

#include <map>
#include <string>

static const uint32_t SCAN_SECONDS = 1;
static const size_t MIN_TX_SPACE = 192;
static const size_t MAX_NAME_BYTES = 32;

static BLEScan *scanner;
static uint32_t last_hb_ms = 0;
static uint32_t advert_count = 0;

static void print_json_string(const uint8_t *s, size_t n) {
  Serial.print('"');
  for (size_t i = 0; i < n; i++) {
    uint8_t c = s[i];
    if (c == '"' || c == '\\') {
      Serial.print('\\');
      Serial.print((char)c);
    } else if (c >= 0x20 && c < 0x7f) {
      Serial.print((char)c);
    } else {
      Serial.print('?');  // keep the line valid ASCII JSON
    }
  }
  Serial.print('"');
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("{\"boot\":\"ble_scan\",\"fw\":\"0.1\"}");

  BLEDevice::init("");
  scanner = BLEDevice::getScan();
  scanner->setActiveScan(false);  // passive: never transmit scan requests
  scanner->setInterval(100);
  scanner->setWindow(99);

  Serial.println("{\"ready\":true,\"mode\":\"passive\"}");
}

void loop() {
  uint32_t now = millis();
  if (now - last_hb_ms >= 5000) {
    last_hb_ms = now;
    if (Serial.availableForWrite() >= 64) {
      Serial.printf("{\"hb\":%lu,\"adverts\":%lu}\n",
                    (unsigned long)now, (unsigned long)advert_count);
    }
  }

  BLEScanResults *results = scanner->start(SCAN_SECONDS, false);
  advert_count += results->getCount();

  // Dedupe by address: newest RSSI in the window wins, name captured once.
  std::map<std::string, int> by_addr;
  std::map<std::string, String> name_of;
  for (uint32_t i = 0; i < results->getCount(); i++) {
    BLEAdvertisedDevice dev = results->getDevice(i);
    std::string addr = dev.getAddress().toString().c_str();
    by_addr[addr] = dev.getRSSI();
    if (name_of.find(addr) == name_of.end()) {
      String nm = dev.haveName() ? dev.getName() : String();
      if (nm.length() > MAX_NAME_BYTES) {
        nm = nm.substring(0, MAX_NAME_BYTES);
      }
      name_of.insert({addr, nm});
    }
  }

  for (auto &kv : by_addr) {
    if (Serial.availableForWrite() < MIN_TX_SPACE) continue;
    Serial.printf("{\"ts_ms\":%lu,\"mac\":\"%s\",\"rssi\":%d,\"name\":",
                  (unsigned long)millis(), kv.first.c_str(), kv.second);
    auto it = name_of.find(kv.first);
    if (it != name_of.end() && it->second.length() > 0) {
      print_json_string((const uint8_t *)it->second.c_str(),
                        it->second.length());
    } else {
      Serial.print("null");
    }
    Serial.println("}");
  }
  scanner->clearResults();
}
