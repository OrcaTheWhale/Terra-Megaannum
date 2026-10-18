// ESP32 -> Python: sends all sensor readings as one comma-separated line, 10 times a second.
//
//   S,millis,temperature,humidity,light,flame,tilt,direction
//   S,15320,22.0,45.0,1874,4095,12.5,135
//
//   temperature  C (DHT11, updates every 2 s; nan if no reading)
//   humidity     % (DHT11)
//   light        0-4095 (photoresistor, raw)
//   flame        0-4095 (flame sensor, raw; drops near a flame or IR remote)
//   tilt         WIND STRENGTH from the joystick: 0 (centred) to 30 (pushed all the way).
//                Sent as "degrees" 0-30 so the Python side (CALIBRATION 'tilt': (0, 30))
//                works exactly as it did with the GY-521 pendulum.
//   direction    degrees 0-360, which way the joystick is pushed = which way the wind blows
//                (-1 when centred)
//
// Wiring (everything + to 3V3, NOT 5V, and - to the shared GND rail):
//   DHT11          S   -> D26
//   Photoresistor  S   -> D32
//   Flame sensor   AO  -> D33
//   Joystick       VRx -> D34,  VRy -> D35,  +5V pin -> 3V3 (yes, 3V3), GND -> GND
//                  (SW not used)
// Leave the joystick centred while the ESP32 starts: it measures its own centre then.

#include <Arduino.h>
#include <DHT.h>

const int DHT_PIN   = 26;
const int LIGHT_PIN = 32;
const int FLAME_PIN = 33;
const int JOY_X_PIN = 34;      // input-only analog pins, perfect for a joystick
const int JOY_Y_PIN = 35;

// If the wind blows the wrong way on screen, flip these (true/false) and upload again.
const bool FLIP_X = false;
const bool FLIP_Y = false;
const bool SWAP_XY = false;

const float DEADZONE = 0.08;   // ignore small wobbles around the centre (8% of full push)

DHT dht(DHT_PIN, DHT11);

float centreX = 2048, centreY = 2048;
float temperature = NAN, humidity = NAN;
unsigned long lastDht = 0;

void setup() {
  Serial.begin(115200);
  delay(500);
  analogReadResolution(12);
  dht.begin();

  // the joystick's resting point is rarely exactly 2048: measure it while centred
  long sx = 0, sy = 0;
  for (int i = 0; i < 50; i++) {
    sx += analogRead(JOY_X_PIN);
    sy += analogRead(JOY_Y_PIN);
    delay(5);
  }
  centreX = sx / 50.0;
  centreY = sy / 50.0;
}

// -1..1 from the centre, using the distance to whichever end is on that side
float axis(int raw, float centre) {
  float d = raw - centre;
  return d >= 0 ? d / (4095 - centre) : d / centre;
}

void loop() {
  if (millis() - lastDht > 2000) {         // DHT11 is slow
    float t = dht.readTemperature(), h = dht.readHumidity();
    if (!isnan(t)) temperature = t;
    if (!isnan(h)) humidity = h;
    lastDht = millis();
  }

  int light = analogRead(LIGHT_PIN);
  int flame = analogRead(FLAME_PIN);

  // joystick -> wind strength (0-30) and direction (0-360)
  float x = axis(analogRead(JOY_X_PIN), centreX);
  float y = axis(analogRead(JOY_Y_PIN), centreY);
  if (SWAP_XY) { float t = x; x = y; y = t; }
  if (FLIP_X) x = -x;
  if (FLIP_Y) y = -y;
  float push = constrain(sqrt(x * x + y * y), 0.0, 1.0);
  float tilt = 0, dir = -1;
  if (push > DEADZONE) {
    tilt = 30.0 * (push - DEADZONE) / (1.0 - DEADZONE);
    dir = degrees(atan2(y, x));
    if (dir < 0) dir += 360;
  }

  Serial.printf("S,%lu,%.1f,%.1f,%d,%d,%.1f,%.0f\n",
                millis(), temperature, humidity, light, flame, tilt, dir);
  delay(100);
}
