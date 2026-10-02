#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <Wire.h>
#include <time.h>
#include <PubSubClient.h>

// ======================= 1. CONFIGURATION À ADAPTER =======================
#define USE_TLS 0  // 0 : broker.hivemq.com:1883 (public, non chiffré)
                   // 1 : votre cluster HiveMQ Cloud:8883 (TLS)

// Wi-Fi : "Wokwi-GUEST" dans le simulateur
const char* WIFI_SSID     = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";
const int   WIFI_CHANNEL  = 6;

// Identifiants EHPAD
const char* TEAM_ID     = "Lyon1"; 
const char* RESIDENT_ID = "R8";     
const char* DEVICE_ID   = "esp32-01";

#if USE_TLS
const char*    MQTT_HOST = "VOTRE-CLUSTER.s1.eu.hivemq.cloud";
const uint16_t MQTT_PORT = 8883;
const char*    MQTT_USER = "UTILISATEUR_TP";
const char*    MQTT_PASS = "MOT_DE_PASSE_TP";
const char* ROOT_CA = R"PEM(
-----BEGIN CERTIFICATE-----
COLLEZ ICI LE CERTIFICAT RACINE (format PEM)
-----END CERTIFICATE-----
)PEM";
WiFiClientSecure netClient;
#else
// Broker public pour Wokwi
const char*    MQTT_HOST = "broker.hivemq.com";
const uint16_t MQTT_PORT = 1883;
const char*    MQTT_USER = nullptr;
const char*    MQTT_PASS = nullptr;
WiFiClient netClient;
#endif

// ======================= 2. BROCHAGE =======================
const int PIN_SOS    = 18;
const int PIN_BUZZER = 19;
const int PIN_HR_POT = 34;
const int PIN_SDA    = 21;
const int PIN_SCL    = 22;
const uint8_t MPU_ADDR = 0x68;

// ======================= 3. PARAMÈTRES =======================
const unsigned long PUBLISH_PERIOD_MS = 2000;
const unsigned long IMU_PERIOD_MS     = 20;
const unsigned long ALARM_DURATION_MS = 3000;
const float FALL_THRESHOLD_G = 2.5;
// Seuils de FC
const int HR_DANGER_LOW = 40, HR_WARNING_LOW = 50, HR_WARNING_HIGH = 110, HR_DANGER_HIGH = 130;

// ======================= 4. ÉTAT =======================
PubSubClient mqtt(netClient);

String topicVitals, topicAlerts, topicStatus, clientId;
bool imuOk = false;
float ax = 0, ay = 0, az = 0;
float peakG = 0;
unsigned long lastPublish = 0, lastImu = 0, lastMqttAttempt = 0, alarmUntil = 0;
unsigned long lastFallAlert = 0, seq = 0;
int lastButton = HIGH;
unsigned long lastButtonChange = 0;
String lastHrLevel = "info";

// ======================= 5. MPU-6050 =======================
void mpuWrite(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.write(value);
  Wire.endTransmission();
}

bool mpuBegin() {
  Wire.beginTransmission(MPU_ADDR);
  if (Wire.endTransmission() != 0) return false;
  mpuWrite(0x6B, 0x00);
  mpuWrite(0x1C, 0x10);
  return true;
}

void mpuReadAccel() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, (uint8_t)6);
  int16_t rx = (Wire.read() << 8) | Wire.read();
  int16_t ry = (Wire.read() << 8) | Wire.read();
  int16_t rz = (Wire.read() << 8) | Wire.read();
  ax = rx / 4096.0;
  ay = ry / 4096.0;
  az = rz / 4096.0;
}

// ======================= 6. OUTILS =======================
String isoTimestamp() {
  time_t now = time(nullptr);
  if (now < 1700000000) return "";
  struct tm t;
  gmtime_r(&now, &t);
  char buf[25];
  strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &t);
  return String(buf);
}

int readHeartRate() {
  int raw = analogRead(PIN_HR_POT);
  int bpm = map(raw, 0, 4095, 30, 180);
  bpm += (int)random(-2, 3);
  return constrain(bpm, 30, 180);
}

String hrLevel(int bpm) {
  if (bpm < HR_DANGER_LOW || bpm > HR_DANGER_HIGH) return "danger";
  if (bpm < HR_WARNING_LOW || bpm > HR_WARNING_HIGH) return "warning";
  return "info";
}

void startAlarm() {
  tone(PIN_BUZZER, 2000);
  alarmUntil = millis() + ALARM_DURATION_MS;
}

// ======================= 7. RÉSEAU =======================
void connectWifi() {
  Serial.printf("Wi-Fi : connexion à %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD, WIFI_CHANNEL);
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print(".");
  }
  Serial.printf("\nWi-Fi OK, IP = %s\n", WiFi.localIP().toString().c_str());
  configTime(0, 0, "pool.ntp.org", "time.google.com");
}

bool connectMqtt() {
  Serial.printf("MQTT : connexion à %s:%u (client %s)... ", MQTT_HOST, MQTT_PORT, clientId.c_str());
  const char* willMsg = "{\"state\":\"offline\"}";
  bool ok = mqtt.connect(clientId.c_str(), MQTT_USER, MQTT_PASS,
                         topicStatus.c_str(), 1, true, willMsg);
  if (ok) {
    Serial.println("OK");
    char online[80];
    snprintf(online, sizeof(online), "{\"state\":\"online\",\"device_id\":\"%s\"}", DEVICE_ID);
    mqtt.publish(topicStatus.c_str(), online, true);
  } else {
    Serial.printf("échec, état = %d\n", mqtt.state());
  }
  return ok;
}

// ======================= 8. PUBLICATIONS =======================
void publishAlert(const char* type, const char* level, double value) {
  char payload[256];
  snprintf(payload, sizeof(payload),
           "{\"resident_id\":\"%s\",\"device_id\":\"%s\",\"type\":\"%s\",\"level\":\"%s\","
           "\"value\":%.2f,\"timestamp\":\"%s\"}",
           RESIDENT_ID, DEVICE_ID, type, level, value, isoTimestamp().c_str());
  bool ok = mqtt.publish(topicAlerts.c_str(), payload);
  Serial.printf("[ALERTE %s] %s -> %s\n", ok ? "envoyée" : "NON envoyée", topicAlerts.c_str(), payload);
}

void publishVitals() {
  int bpm = readHeartRate();
  String level = hrLevel(bpm);

  char payload[384];
  snprintf(payload, sizeof(payload),
           "{\"resident_id\":\"%s\",\"device_id\":\"%s\",\"source\":\"esp32\",\"seq\":%lu,"
           "\"timestamp\":\"%s\",\"heart_rate\":%d,"
           "\"accel_g\":{\"x\":%.2f,\"y\":%.2f,\"z\":%.2f},\"accel_peak_g\":%.2f,"
           "\"imu_ok\":%s,\"alert_level\":\"%s\"}",
           RESIDENT_ID, DEVICE_ID, seq++, isoTimestamp().c_str(), bpm,
           ax, ay, az, peakG, imuOk ? "true" : "false", level.c_str());
  bool ok = mqtt.publish(topicVitals.c_str(), payload);
  Serial.printf("[%s] %s\n", ok ? "PUB" : "ERREUR PUB", payload);

  if (level != lastHrLevel && level != "info") {
    publishAlert("hr_out_of_range", level.c_str(), bpm);
    if (level == "danger") startAlarm();
  }
  lastHrLevel = level;
  peakG = 0;
}

// ======================= 9. CAPTEURS LOCAUX =======================
void readImu() {
  if (!imuOk) return;
  mpuReadAccel();
  float norm = sqrt(ax * ax + ay * ay + az * az);
  if (norm > peakG) peakG = norm;

  if (norm > FALL_THRESHOLD_G && millis() - lastFallAlert > 10000) {
    lastFallAlert = millis();
    publishAlert("fall_suspected", "danger", norm);
    startAlarm();
  }
}

void readSosButton() {
  int state = digitalRead(PIN_SOS);
  if (state != lastButton && millis() - lastButtonChange > 50) {
    lastButtonChange = millis();
    lastButton = state;
    if (state == LOW) {
      publishAlert("sos", "danger", 1);
      startAlarm();
    }
  }
}

// ======================= 10. SETUP / LOOP =======================
void setup() {
  Serial.begin(115200);
  pinMode(PIN_SOS, INPUT_PULLUP);
  pinMode(PIN_BUZZER, OUTPUT);
  analogReadResolution(12);

  Wire.begin(PIN_SDA, PIN_SCL);
  imuOk = mpuBegin();
  Serial.println(imuOk ? "MPU-6050 détecté (0x68)"
                       : "MPU-6050 introuvable : vérifiez SDA=21, SCL=22, VCC=3V3, GND");

  // --- ADAPTATION DES TOPICS POUR L'ARCHITECTURE EHPAD ---
  String base = String("ehpad/residents/") + RESIDENT_ID;
  topicVitals = base + "/vitals";
  topicAlerts = "ehpad/alerts"; // Topic global des alertes
  topicStatus = String("ehpad/device/") + DEVICE_ID + "/status";
  
  clientId = String("digi5-") + TEAM_ID + "-" + DEVICE_ID + "-" + String((uint32_t)random(0xFFFF), HEX);

  connectWifi();
#if USE_TLS
  netClient.setCACert(ROOT_CA);
#endif
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setBufferSize(512);
  mqtt.setKeepAlive(30);
}

void loop() {
  if (!mqtt.connected() && millis() - lastMqttAttempt > 5000) {
    lastMqttAttempt = millis();
    connectMqtt();
  }
  mqtt.loop();

  unsigned long now = millis();
  if (now - lastImu >= IMU_PERIOD_MS) { lastImu = now; readImu(); }
  readSosButton();
  if (now - lastPublish >= PUBLISH_PERIOD_MS && mqtt.connected()) {
    lastPublish = now;
    publishVitals();
  }
  if (alarmUntil && now > alarmUntil) { noTone(PIN_BUZZER); alarmUntil = 0; }
}