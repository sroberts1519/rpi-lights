#!/user/bin/env python3

import serial.tools.list_ports

pi_version = {'a020d3':"3B+", 'a02082':"3B", 'a22082':"3B"}

def getrevision():
  # Extract board revision from cpuinfo file
  myrevision = "0000"
  try:
    f = open('/proc/cpuinfo','r')
    for line in f:
      if line[0:8]=='Revision':
        length=len(line)
        myrevision = line[11:length-1]
    f.close()
  except:
    myrevision = "0000"
 
  return myrevision

pi_ver = pi_version[getrevision()]
print("Pi version: ", pi_ver)

ports = serial.tools.list_ports.comports()

vendor_id = {9025:"Arduino", 5824:"Teensy"}
product_id = {66:"Mega R3 (Atmega2560)", 67:"Uno R3 (Atmega328)", 1155:"Teensy 3.2"}
usb_port_3B = {'2':"upper left", '3':"lower left", '4':"upper right", '5':"lower right"}
usb_port_3Bplus = {'1.2':"upper left", '1.3':"lower left", '3':"upper right", '2':"lower right"}

for a in ports:
    if a.subsystem == 'usb':
       #print (int(a.location[4])-2)
       
       if pi_ver == '3B':
          print ("\nUSB Port Full: " + a.location + " (" + usb_port_3B[a.location[4]] + ")")
          print ("USB Port Short: " + a.location[4:])
       else:
          print ("\nUSB Port Full: " + a.location + " (" + usb_port_3Bplus[a.location[4:]] + ")")
          print ("USB Port Short: " + a.location[4:])
                 
       print ("device: ", a.device)
       print ("Manufacturer String: ", a.manufacturer)
       try:
           print ("Vendor ID: ", a.vid, ", ", vendor_id[a.vid])
       except:
           print ("Vendor ID: ", a.vid, " (unknown)")
       try:
           print ("Product ID (pid): ", a.pid, ", ", product_id[a.pid])
       except:
           print ("Product ID (pid): ", a.pid, " (unknown)")
       # get last two digits of serial number    
       print ("Controller ID (serial number): ", a.serial_number[len(a.serial_number)-2:])
print(" ")       
     
