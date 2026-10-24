/*
 * wifi_probe — ESP32-S3 passive 802.11 probe-request scanner.
 *
 * Hops channels 1-11 every 400 ms in promiscuous mode and prints one JSON
 * object per probe request over USB serial:
 *
 *   {"ts_ms":12345,"mac":"a4:5e:60:1a:2b:3c","rssi":-63,"ch":6,"ssid":"Flock-1A2B3C"}
 *
 * Wildcard probes (empty SSID) print "ssid":null. Frames are dropped when the
 * USB TX buffer is nearly full so a slow/absent reader can never stall the
 * sniffer. No association, no transmission: receive-only.
 *
 * Build: see README.md in this directory.
 */
#include <Arduino.h>
#include <WiFi.h>
#include <esp_wifi.h>

static const uint8_t CHANNELS[] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11};
static const uint32_t HOP_INTERVAL_MS = 400;
static const size_t MIN_TX_SPACE = 192;

static uint8_t channel_index = 0;
static uint32_t last_hop_ms = 0;
static uint32_t last_hb_ms = 0;
static volatile uint32_t probe_count = 0;

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

static void sniffer_cb(void *buf, wifi_promiscuous_pkt_type_t type) {
  if (type != WIFI_PKT_MGMT) return;

  const wifi_promiscuous_pkt_t *pkt = (const wifi_promiscuous_pkt_t *)buf;
  const uint8_t *frame = pkt->payload;
  uint16_t len = pkt->rx_ctrl.sig_len;
  if (len > 4) len -= 4;  // sig_len includes the 4-byte FCS
  if (len < 24) return;

  // 802.11 management frame, subtype 4 = probe request.
  if (((frame[0] >> 2) & 0x3) != 0) return;
  if (((frame[0] >> 4) & 0xf) != 4) return;

  probe_count++;

  const uint8_t *p = frame + 24;  // tagged parameters start after MAC header
  const uint8_t *end = frame + len;
  const uint8_t *ssid = nullptr;
  uint8_t ssid_len = 0;
  while (p + 2 <= end) {
    uint8_t tag = p[0];
    uint8_t tlen = p[1];
    if (p + 2 + tlen > end) break;
    if (tag == 0) {  // SSID
      ssid = p + 2;
      ssid_len = tlen > 32 ? 32 : tlen;
      break;
    }
    p += 2 + tlen;
  }

  if (Serial.availableForWrite() < MIN_TX_SPACE) return;

  const uint8_t *a = frame + 10;  // addr2 = transmitter
  char mac[18];
  snprintf(mac, sizeof(mac), "%02x:%02x:%02x:%02x:%02x:%02x",
           a[0], a[1], a[2], a[3], a[4], a[5]);

  Serial.printf("{\"ts_ms\":%lu,\"mac\":\"%s\",\"rssi\":%d,\"ch\":%u,\"ssid\":",
                (unsigned long)millis(), mac, (int)pkt->rx_ctrl.rssi,
                (unsigned)pkt->rx_ctrl.channel);
  if (ssid != nullptr && ssid_len > 0) {
    print_json_string(ssid, ssid_len);
  } else {
    Serial.print("null");
  }
  Serial.println("}");
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("{\"boot\":\"wifi_probe\",\"fw\":\"0.1\"}");

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  wifi_promiscuous_filter_t filter = {};
  filter.filter_mask = WIFI_PROMIS_FILTER_MASK_MGMT;
  esp_wifi_set_promiscuous_filter(&filter);
  esp_wifi_set_promiscuous_rx_cb(&sniffer_cb);
  esp_wifi_set_promiscuous(true);
  esp_wifi_set_channel(CHANNELS[0], WIFI_SECOND_CHAN_NONE);

  Serial.printf("{\"ready\":true,\"channels\":%u}\n",
                (unsigned)(sizeof(CHANNELS) / sizeof(CHANNELS[0])));
}

void loop() {
  uint32_t now = millis();
  if (now - last_hop_ms >= HOP_INTERVAL_MS) {
    last_hop_ms = now;
    channel_index = (channel_index + 1) % (sizeof(CHANNELS) / sizeof(CHANNELS[0]));
    esp_wifi_set_channel(CHANNELS[channel_index], WIFI_SECOND_CHAN_NONE);
  }
  if (now - last_hb_ms >= 5000) {
    last_hb_ms = now;
    if (Serial.availableForWrite() >= 64) {
      Serial.printf("{\"hb\":%lu,\"probes\":%lu}\n",
                    (unsigned long)now, (unsigned long)probe_count);
    }
  }
  delay(5);
}
