#!/user/bin/env python3

import RPi.GPIO as GPIO
import time
import serial
from shift import Shifter
import sys
import socket

class Sub_Ctrl:
   def __init__(self, act_sub_ctrl, ctrltype, startch, numch, data, clock, latch, usb, port):
      self.ctrl_type = ctrltype
      self.start = startch
      self.num_ch = numch
      self.data = data
      self.clock = clock
      self.latch = latch
      self.usb = usb
      self.error = False
      self.port = port
      
      if act_sub_ctrl:     #activate sub_ctrller - set to false for fseq parse
         if self.ctrl_type == "shift":
            self.shift_ctrl()
         if self.ctrl_type == "pixel":
            self.pixel_ctrl()

   def shift_ctrl(self):
      print("\nPreparing connection with shift registers")
      GPIO.setmode(GPIO.BCM)
      self.lights = Shifter(self.data, self.clock, self.latch, self.num_ch)
      self.lights.clear()     #turn off all channels

   def pixel_ctrl(self):
      print("Preparing connection with pixel controller on usb", self.usb, "port", self.port)
      try:
         self.serial = serial.Serial(self.usb, 115200, timeout=0.1)     #set timeout to 100 msec
      except:
         print("Could not open connection with pixel controller on ", self.usb, "port", self.port)
         self.error = True
      # turn off all pixels on sub_ctrl
      self.serial.write(b'START' + b'\x00'*self.num_ch + b'END')
      return
 
class Controller:
   def __init__(self, addr, index, max_error=0):
               #from config.xml
      self.index = index
      self.ip_addr = addr
               #other variables
      self.name = None
      self.start_ch = None   #set when we read network.xml file
      self.tot_num_ch = 0
      self.available = False
      self.socket = None
      self.sub_ctrl = []
      self.prev = None
      self.curslice = None
      self.is_local = False
      self.error = False
      self.out_file = None
      self.connected = False
      self.error_count = 0
      self.max_error = max_error
     
   def add_shift_sub(self, act_sub_ctrl, startch, numch, data, clock, latch):
      self.sub_ctrl.append(Sub_Ctrl(act_sub_ctrl, 'shift', startch, numch, data, clock, latch, None, None))
      self.tot_num_ch += numch

   def add_pixel_sub(self, act_sub_ctrl, startch, numch, usb, port):
      self.sub_ctrl.append(Sub_Ctrl(act_sub_ctrl, 'pixel', startch, numch, None, None, None, usb, port))
      self.tot_num_ch += numch

   def check_start_end(self):
      # see outputtolights for information on two-way communication between
      # director and remote controller
      # if received message was good, respond to director with RECEIVED
      # if received message was bad, respond to director with FLUSHED
      if self.curslice[0:5] != b'START' or self.curslice[len(self.curslice)-3:] != b'END':
         print("Error in received message.  Did not begin with START or did not end with END")
         print("Flushing message slice")
         self.socket.sendall(b'FLUSHED')
         self.curslice = None
         return False
      else:
         self.socket.sendall(b'RECEIVED')
         self.curslice = self.curslice[5:-3]     #strip off START and END
         return True
    
   #######################################
   # routine to output list l to lights  #
   #######################################
   def outputtolights(self):
      #   for index, type in enumerate(CTRLTYPE):
      #  Protocol is to send the STARTchanneldataEND message to remote controller
      #  remote controller will respond with either:
      #      RECEIVED   - successful
      #      FLUSHED    - not successful
      #  The two-way communication was created so that the director
      #   can determine if the remote controller is no longer responding.
      #  The round trip is usually less then 1.5 msec.  on very rare occasion, it
      #   can be as much as 4.5 msec.  This data was from testing.
      #  If this two way communication proves to be too slow in the future,
      #   then change to only checking to see if the remote controller is responding
      #   between songs.

      #  Performance testing:
      #  24 ch shift took approx. 600-700 micro seconds
      #  30 pixels at 115k baud to arduino took approx 6-7 milliseconds
      
      if self.is_local:
         for c in self.sub_ctrl:
            if c.ctrl_type == "shift":
               ov = 0
               #  The proper range we want is curslice[start-1:start+numch-1]
               # convert bytes to bits !0 byte is a 1 bit
               for i in self.curslice[c.start-1:c.start+c.num_ch-1]:
                  ov = ov << 1
                  if i != 0:
                     ov = ov | 1
               c.lights.output(ov)
            elif c.ctrl_type == "pixel":
               c.serial.write(b'START' + self.curslice[c.start-1:c.start+c.num_ch-1] + b'END')
         return False
      else:   # controller is remote
         try:
            self.socket.sendall(b'START' + self.curslice + b'END')
         except:
            print("\nError sendind data slice to controller index:", self.index, "IP addr:", self.ip_addr)
            print("Error: ", sys.exc_info()[0])
            return True
         try:
            data = self.socket.recv(16)
         except:
            print("\nWhile sending a data slice to controller an error occured.")
            print("Controller:", self.index, "IP address:", self.ip_addr, "Name:", self.name)
            print("Error: ", sys.exc_info()[0])
            return True
         if data != b'RECEIVED':
            print("Controller ", self.index, self.ip_addr, self.name, " did not receive last message correctly")
            self.error_count += 1
            if self.error_count >= self.max_error:
               print("There have been", self.error_count, "with controller", self.index, self.ip_addr, self.name)
               return True
      return False

   def send_sync_msg(self, t):
      try:
         self.socket.sendall(b'SYNC' + str(t).encode() + b'END')
         data = self.socket.recv(16)
      except:
         print("Error sending sync message to controller: ", self.index, self.ip_addr, self.name)
         print("Error: ", sys.exc_info()[0])
         return True
      if data != b'RECEIVED':
         print("Controller , ", self.index, self.ip_addr, self.name, " did not receive sync message correctly")
      return False

   def open_conn(self, port):
      #################################################
      # Open TCP/IP connection with remote controller #
      #################################################
      try:
         self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
         self.socket.settimeout(5)
         print("\nTrying to open connection with controller index:", self.index, "IP address:", self.ip_addr)
         self.socket.connect((self.ip_addr, port))
      except:
         print("\nCommunication error while trying to connect to controller ", self.index, self.ip_addr)
         return False
      try:
         message = self.socket.recv(64)
      except:
         print("While waiting for a connection acknowledgement from controller an error occured")
         print("Controller index: ", self.index, "controller IP address:", self.ip_addr, "Controller name:", self.name)
         print("Error: ", sys.exc_info()[0])
         return False
      if not message.decode() == "CONNECTSUCCESS":
         print("Did not receive successful connection acknowledgement from controller: ", self.index, self.ip_addr)
         return False
      print("Successfully opened connection with controller index:", self.index, "IP address:", self.ip_addr)
      self.connected = True

      #########################################
      # Request configuration from controller #
      #########################################
      print("Requesting configuration information from controller index:", self.index, "IP address:", self.ip_addr)
      self.socket.settimeout(0.01)
      self.socket.sendall(b'SENDCONFIG')
      try:
         addrcheck = self.socket.recv(64)
      except self.socket.timeout:
         print("Communication timeout waiting for response from controller ", self.index, self.ip_addr)
         return False
      acl = addrcheck.decode().split(" ") #split into list acl (addrchecklist)
      if len(acl) != 6 or acl[0] != "address" or acl[2] != "index" or acl[4] != "numch":
         print ("Invalid configuration response from controller: ", c.index, " address: ", self.ip_addr)
         print ("Got:  ", acl)
         print ("should be: ['address', 'IP ADDRESS', 'index', 'number', 'numch', 'number']")
         self.socket.sendall(b'ERROR')
         return False
      if acl[1] != self.ip_addr:
         print("Controller: ", c.index, " IP address in it's config.xml (", acl[1],")")
         print("                does not match physical IP address (", self.ip_addr,")")
         self.socket.sendall(b'ERROR')
         return False
      if int(acl[3]) != self.index:
         print("Controller: ", self.index, " controller number in it's config.xml (", acl[3], ")")
         print("                does not match index in director's attributes controller list (", self.index, ")")
         self.socket.sendall(b'ERROR')
         return False
      self.socket.sendall(b'CONFIGACK')
      self.tot_num_ch = int(acl[5])
      return True

   def lights_off(self):
      for s in self.sub_ctrl:
         if s.ctrl_type == "shift":
            s.lights.clear()     #turn off all channels
            continue
         if s.ctrl_type == "pixel":
            s.serial.write(b'START' + b'\x00'*s.num_ch + b'END')
            continue
   
   def sig_end_of_song(self):
      if not self.is_local and self.available:
         print("\nSignaling controller: ", self.index, self.ip_addr, self.name, " end of song")
         self.available = False
         try:
            self.socket.sendall("ENDOFSONG".encode())
            message = self.socket.recv(16)
         except:
            print("Error sending ENDOFSONG code to controller index:", self.index, "IP address", self.ip_addr)
            print("Error: ", sys.exc_info()[0])
            return False
         if not message.decode() == "ENDOFSONGACK":
            print("Controller IP address:", self.ip_addr, "did not send us correct acknowledgement to ENDOFSONG")
            return False
      else:      # self is_local - turn lights off
         self.lights_off()
      return True

   def sig_end_of_show(self):
      if not self.is_local:
         print("\nSignaling controller: ", self.index, self.ip_addr, self.name, " end of show")
         try:
            self.socket.sendall("ENDOFSHOW".encode())
            message = self.socket.recv(16)
         except:
            print("Error sending ENDOFSHOW code to controller index:", self.index, "IP address", self.ip_addr)
            print("Error: ", sys.exc_info()[0])
            return False
            return False
         if not message.decode() == "ENDOFSHOWACK":
            print("Controller IP address:", self.ip_addr, "did not send us correct acknowledgement to ENDOFSHOW")
            return False         
      return True
   
   def close(self):
      if self.is_local:
         for c in self.sub_ctrl:
            if c.ctrl_type == "shift":
               print("Cleaning up connection with local shift registers")
               c.lights.clear()
               time.sleep(0.2)
               GPIO.cleanup()
            if c.ctrl_type == "pixel":
               print("Closing connection to local pixel controller on port ", c.usb)
               # turn off all pixels on sub_ctrl
               c.serial.write(b'START' + b'\x00'*c.num_ch + b'END')
               c.serial.close()
               
      else:   #remote controller
         if self.connected:
            print("Signaling controller: ", self.index, self.ip_addr, self.name, " to exit")

            # need try statement with sendall in this instance because socket
            # may already been broken with previous failed communicaiton attempts
            try:      
               self.socket.sendall("EXITNOW".encode())
               message = self.socket.recv(16)
            except:
               print("Comm error with controller: ", self.index, self.ip_addr, self.name, " while sending EXITNOW code")
            else:   
               print("Closing socket with controller ", self.index, self.ip_addr, self.name)
               if not message.decode() == "EXITNOWACK":
                  print("Controller IP address:", self.ip_addr, "did not send us correct acknowledgement to EXITNOW")
               self.socket.close()
         else:   # controller was never attached no reason to close connection
            print("Controller: ", self.index, self.ip_addr, self.name, " was never connected.  Don't need to close connection")

