#include<OctoWS2811.h>
//Data is sent strip 1 first through strip 8 last
// strip_num_leds is an array of actual pixels in strip per vixen config.
// Each element of the array is a TEENSY channel - thus array of 8

int strip_num_leds[8] = {400,0,0,0,0,0,0,0};

// POWER is the power level of the leds as a percent.  i.e. .5 = 50%
const float POWER = .2;

//ledsPerStrip is the number of LEDs connected to each pin,
//   or maximum number if different on each pin 
const int ledsPerStrip = 400;

//displayMemory - the meomory used for display data.
//   Use an array of "int" 6 times ledsPerStrip.
DMAMEM int displayMemory[ledsPerStrip*6];

//drawingMemory - The memory used for drawing operations.
//   Use iether an arror of "int" 6 times ledsPerStrip,
//   or NULL to perform all drawing directly to the display memory.
int drawingMemory[ledsPerStrip*6];

//WS2811config - configure the WS2811 speed and LED color order.
//   Options:  WS2811_RGB, WS2811_RBG, WS2811_GRB, WS2811_GBR
//             WS2811_800kHz, WS2811_400kHz
const int WS2811config = WS2811_RGB | WS2811_800kHz;

OctoWS2811 leds(ledsPerStrip, displayMemory, drawingMemory, WS2811config);

int incomingByte = 0;
int indx = 0;
const char *header = "START";
const char *footer = "END";
const int ledPin = 13;

int Location = 1;    // 1=Header, 2=Body, Footer=3
//CRGB leds[NUM_LEDS];
byte readbuffer[3];
int i;
int x;
int pixelnumber;

void setup() {
  Serial.begin(115200);
  pinMode(ledPin, OUTPUT);
  //Turn LED on to signify that Teensy is up and running
  digitalWrite(ledPin, HIGH);
  leds.begin();
  leds.show();
}

void loop() {
  if (Serial.available()) {
    switch (Location) {
      case 1:    //header
        //Serial.println("Reading Header");
        incomingByte = Serial.read();
        //Serial.println((char)incomingByte);
        if (incomingByte == header[indx]) {
          indx++;
        } else {
          indx = 0;
        }
        if (indx == 5) {
          indx = 0;
          Location = 2;
        }
        break;
      case 2:   // body
        //Serial.println("Reading Body");
        for (i=0; i < 8; i++) {
          pixelnumber = i * ledsPerStrip; //starting pixel number for the current strip
          for (x=0; x < strip_num_leds[i]; x++) {
            //Serial.println("Pixel");
            Serial.readBytes((char*)readbuffer, 3);
            //leds.setPixel(pixnum, red, green, blue)
            leds.setPixel(pixelnumber++, readbuffer[0]*POWER, readbuffer[1]*POWER, readbuffer[2]*POWER); 
          }
        }
        Location = 3;
        indx = 0;
        //Serial.println("Finished reading body");
        break;
      case 3:   // footer
        //Serial.println("Reading Footer");
        incomingByte = Serial.read();
        //Serial.println((char)incomingByte);
        if (incomingByte == footer[indx]) { 
          indx++;
        }
        else { //Footer field not correct.  flush message and look for header again
          indx = 0;
          Location = 1;
        }
        if (indx == 3) {
          indx = 0;
          Location = 1;
          leds.show();
        }
        break;
    }
  }
}
