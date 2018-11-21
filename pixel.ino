#include <FastLED.h>
#define NUM_LEDS 30
#define DATA_PIN 2
#define BRIGHT 25

int incomingByte = 0;
int index = 0;
char *header = "START";
char *footer = "END";
int Location = 1;    // 1=Header, 2=Body, Footer=3
CRGB leds[NUM_LEDS];

void setup() {
  Serial.begin(115200);
  FastLED.addLeds<NEOPIXEL, DATA_PIN>(leds, NUM_LEDS);
  FastLED.setBrightness(BRIGHT);
}

void loop() {
  if (Serial.available()) {
    switch (Location) {
      case 1:    //header
        incomingByte = Serial.read();
        if (incomingByte == header[index]) {
          index++;
        } else {
          index = 0;
        }
        if (index == 5) {
          index = 0;
          Location = 2;
        }
        break;
      case 2:   // body
        Serial.readBytes((char*)leds, NUM_LEDS*3);
        Location = 3;
        index = 0;
        break;
      case 3:   // footer
        incomingByte = Serial.read();
        if (incomingByte == footer[index]) { 
          index++;
        }
        else { //Footer field not correct.  flush message and look for header again
          index = 0;
          Location = 1;
        }
        if (index == 3) {
          index = 0;
          Location = 1;
          FastLED.show();
        }
        break;
    }
  }
}
