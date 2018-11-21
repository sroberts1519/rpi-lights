#!/user/bin/env python3

# Christmas Light Director Version 2
# Raspberry Pi is the controller

import RPi.GPIO as GPIO

class Shifter():
   
   def __init__(self, data, clock, latch, size):
      self.datapin = data
      self.clockpin = clock
      self.latchpin = latch
      self.size = size
      self.setupboard()

   def setupboard(self):
      GPIO.setup(self.datapin, GPIO.OUT, initial=GPIO.LOW)
      GPIO.setup(self.clockpin, GPIO.OUT, initial=GPIO.LOW)
      GPIO.setup(self.latchpin, GPIO.OUT, initial=GPIO.LOW)

   def clocktick(self):
      GPIO.output(self.clockpin, GPIO.HIGH)
      GPIO.output(self.clockpin, GPIO.LOW)
        
   def latch(self):
      GPIO.output(self.latchpin, GPIO.HIGH)
      GPIO.output(self.latchpin, GPIO.LOW)
        
   def clear(self):
      for i in range(self.size):
         GPIO.output(self.datapin, GPIO.LOW)
         self.clocktick()
      self.latch()

   def output(self, value):
      bit = 2**(self.size - 1)
      for i in range(self.size):
         if (bit&value == 0):
            GPIO.output(self.datapin, GPIO.LOW)
         else:
            GPIO.output(self.datapin, GPIO.HIGH)
         self.clocktick()
         bit = bit>>1
      self.latch()

