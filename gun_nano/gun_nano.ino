#define Laser_Switch   5
#define Laser_nano     3
bool flag = true;
unsigned long laserOnTime = 0;
bool laserActive = false;
const unsigned long laserDuration = 35;  

void setup() {
  Serial.begin(9600);
  pinMode(Laser_Switch, INPUT);
  pinMode(Laser_nano, OUTPUT);
}

void loop() {
  int read_input = digitalRead(Laser_Switch);

  if (read_input == 0 && flag == true) {
    Serial.println("Fired");
    //delay(10);
    tone(Laser_nano, 38000);             
    laserOnTime = millis();               
    laserActive = true;
    flag = false;
  }

  if (laserActive && millis() - laserOnTime >= laserDuration) {
    noTone(Laser_nano);                   
    laserActive = false;
  }

  if (read_input == 1) {
    flag = true;
    Serial.println("Trigger released");
  }
}