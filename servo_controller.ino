#include <Servo.h>

Servo servoX;
Servo servoY;


const int servoXPin = 9;
const int servoYPin = 10;
int posX = 90; // neutral position
int posY = 90; // neutral position

// Higher sensitivity: smaller input range maps to full servo travel.
const int INPUT_RANGE_DEG = 45; // was effectively 90

void setup() {
  Serial.begin(115200);
  servoX.attach(servoXPin);
  servoY.attach(servoYPin);
  servoX.write(posX);
  servoY.write(posY);
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) return;

    int dx = 0;
    int dy = 0;
    int fire = 0;

    // Expected incoming: aim,dx,dy,fire
    if (sscanf(line.c_str(), "aim,%d,%d,%d", &dx, &dy, &fire) >= 2) {
      // Clamp then map a narrower range so movement per command is larger.
      dx = constrain(dx, -INPUT_RANGE_DEG, INPUT_RANGE_DEG);
      dy = constrain(dy, -INPUT_RANGE_DEG, INPUT_RANGE_DEG);

      int targetX = map(dx, -INPUT_RANGE_DEG, INPUT_RANGE_DEG, 0, 180);
      int targetY = map(dy, -INPUT_RANGE_DEG, INPUT_RANGE_DEG, 0, 180);

      servoX.write(targetX);
      servoY.write(targetY);

      if (fire) {
        // simple feedback for prototype
        Serial.println("FIRE");
      }
    }
  }
}
