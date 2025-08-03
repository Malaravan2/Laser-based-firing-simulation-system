#include <WiFi.h>
#include <WiFiUdp.h>

#define TRIGGER_PIN     36  

// WiFi settings
// const char* ssid = "Airtel_Office 4G";
// const char* password = "3dotsinnovations";

const char* ssid = "gunclient";
const char* password = "12345678";
const char* udpAddress = "255.255.255.255"; 
const int udpPort = 4242;

WiFiUDP udp;
int lockcount = 0;
bool blnwait = false;

void setup() {
  Serial.begin(115200);

  pinMode(TRIGGER_PIN, INPUT_PULLUP);

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(100);
    Serial.print(".");
  }
  Serial.println(" Connected!");

  // Print IP of ESP32
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  int triggerState = digitalRead(TRIGGER_PIN);

  if (triggerState == LOW)  // Trigger pulled
  {
    if (!blnwait)
    {
      blnwait = true;
      ++lockcount;

      char msg[64];
      snprintf(msg, sizeof(msg), "shot%d, TRIGGER", lockcount);

      udp.beginPacket(udpAddress, udpPort);
      udp.write((const uint8_t*)msg, strlen(msg));
      udp.endPacket();

      Serial.println(msg);
    }
  }
  else
  {
    blnwait = false;  
  }

  delay(10);
}