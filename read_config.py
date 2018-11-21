#!/user/bin/env python3

###################################
#     read config.xml             #
###################################

import xml.etree.ElementTree
import controller
import serial.tools.list_ports

def get_serial_info(port, serial_num):
   # sample output of USB query
   #Pi version:  3B+
   #
   #USB Port: 1-1.1.2 (upper left)
   #device:  /dev/ttyACM0
   #Manufacturer String:  Teensyduino
   #Vendor ID:  5824 ,  Teensy
   #Product ID (pid):  1155 ,  Teensy 3.2
   #Controller ID (serial number):  10


   vendor_id = {9025:"Arduino", 5824:"Teensy"}
   product_id = {66:"Mega R3 (Atmega2560)", 67:"Uno R3 (Atmega328)", 1155:"Teensy 3.2"}
   #usb_port_3B = {'2':"upper left", '3':"lower left", '4':"upper right", '5':"lower right"}
   #usb_port_3Bplus = {'1.2':"upper left", '1.3':"lower left", '3':"upper right", '2':"lower right"}
   
   ports = serial.tools.list_ports.comports()
   for a in ports:
      if a.subsystem == 'usb' and a.location[4:] == port:     # port listed as 1-1.x where x is 2-5.  port # is x
         #found port - check to see if reported serial num matches configuration
         print ("Device on USB port", port, "reports the following:")
         print ("Manufacturer String: ", a.manufacturer)
         try:
            print ("Vendor ID: ", a.vid, ", ", vendor_id[a.vid])
         except:
            print ("Vendor ID: ", a.vid, " (unknown)")
         try:
            print ("Product ID (pid): ", a.pid, ", ", product_id[a.pid])
         except:
            print ("Product ID (pid): ", a.pid, " (unknown)")
         print ("Controller ID (serial number): ", a.serial_number[len(a.serial_number)-2:])
         print ("device: ", a.device)
         if serial_num == a.serial_number[len(a.serial_number)-2:]:   # check last two digits of reported serial num
            print("\nVerified device on port", port, "serial number matches configuration")
            return a.device
         else:
            print("\nSerial number of device on port", port, "does not match")
            print("Device on port", port, "has serial number",  a.serial_number[len(a.serial_number-2):], "config has serial number", serial_num)
            return False
   # if got here then device not found - error
   print("USB device with serial number: ", serial_num, " not found on port: ", port)
   return False

class Config:
   def __init__(self, isdirector, diraddr, dirctrladdr, dist, prevslice, syncupdate, port, songlist, numoftimes):
      self.port = port
      self.is_director = isdirector
      self.director_addr = diraddr
      self.distributed = dist
      self.prevslice = prevslice
      self.syncupdate = syncupdate
      self.slicesize = 0
      self.ctrl_list = []
      self.error = False
      self.clean_exit = False
      self.songlist = songlist
      self.numoftimes = numoftimes
      if self.is_director:
         for y, x in enumerate(dirctrladdr):
            self.ctrl_list.append(controller.Controller(x[0], y, x[1]))  #x[0] is IP addr, y is index, x[1] is max_error

def readconfig(act_sub_ctrl):
   configerror = False
   DIRECTOR_CTRL_LIST = None
   SYNCUPDATE = None
   SONGLIST = ""
   NUMOFTIMES = 0
   IS_DIRECTOR = None
   DIRECTOR_ADDR = None
   DISTRIBUTED = None
   PREVSLICE = None
   PORT = None

   try:
      treeroot = xml.etree.ElementTree.parse('config.xml').getroot()
   except:
      print("Error in config.xml file.  Please check for valid tags in config.xml")
      print("Error in Config.xml:     ", sys.exc_info()[1])
      configerror = True    

   if not configerror:
      try:
         PORT = int(treeroot.find('Port').text)
      except:
         print("Could not find Port attribuite in config.xml")
         configerror = True

      #########################################
      # find director section                 #
      #########################################
      if treeroot.find('Director_Section'):
         p = treeroot.find('Director_Section')

         #########################################
         # Read DirectorAddr attribute           #
         #########################################
         try:
            DIRECTOR_ADDR = p.find('DirectorAddr').text
         except:
            print("Could not find DirectorAddr attribute in config.xml")
            configerror = True
            DIRECTOR_ADDR = ""

         #########################################
         # Read IsDirector attribute             #
         #########################################
         try:
            if p.find('IsDirector').text == 'Yes':
               IS_DIRECTOR = True
            else:
               IS_DIRECTOR = False
         except:
            print("Could not find IsDirector attribute in config.xml")
            configerror = True
            IS_DIRECTOR = False

         if IS_DIRECTOR:
            #########################################
            # Read CtrlList                         #
            #########################################
            if p.find('CtrlList'):
               p2 = p.find('CtrlList')
               DIRECTOR_CTRL_LIST = []
               for child in p2:
                  if child.tag == "Ctrller":
                     try:
                        ipaddr = child.find('IPAddr').text
                        maxerror = int(child.find('MaxError').text)
                        DIRECTOR_CTRL_LIST.append([ipaddr, maxerror])
                     except:
                        print("Controller in CtrlList (in director section) does not have correct attributes")
                        configerror = True
                  else:
                     print("Under CtrlIPList, child not Ctrller (in config.xml)")
                     configerror = True
            else:
               print("Could not find CtrlList group in config.xml")
               configerror = True

            #########################################
            # Read SongList attribute               #
            #########################################
            if p.find('SongList'):
               SONGLIST = []
               p2 = p.find('SongList')
               for child in p2:
                  if child.tag == "Song":
                     song = child.text
                     SONGLIST.append(song)
                  else:
                     print("Each song in SongList should use Song tag")
                     configerror = True
            else:
               print("Could not find SongList in config.xml")
               configerror = True

            #########################################
            # Read NumberOfTimes attribute          #
            #########################################
            try:
               NUMOFTIMES = int(p.find('NumberOfTimes').text)
            except:
               print("Could not find NumberOfTimes attribute in config.xml")
               configerror = True

         #end reading is_director=yes attributes      

         #########################################
         # Read Distributed and SyncUpdate       #
         #########################################
         try:
            dist = p.find('Distributed').text
         except:
            print("Could not find Distributed attribute in config.xml")
            configerror = True
         if dist == "Yes":
            DISTRIBUTED = True
            try:
               SYNCUPDATE = int(p.find('SyncUpdate').text)
            except:
               print("Could not find SyncUpdate attribute in config.xml")
               configerror = True
         else:
            DISTRIBUTED = False

         #########################################
         # Read PrevSlice attribute              #
         #########################################
         if IS_DIRECTOR or DISTRIBUTED:
            try:
               if p.find('PrevSlice').text == 'Yes':
                  PREVSLICE =  True
               else:
                  PREVSLICE = False
            except:
               print("Could not find PrevSlice attribute in config.xml")
               PREVSLICE = False
               configerror = True
         else:
            PREVSLICE = False

      # End of read direction section
      else:
         print("Director section was not found in config.xml")
         configerror = True

   my_config = Config(IS_DIRECTOR, DIRECTOR_ADDR, DIRECTOR_CTRL_LIST,
                      DISTRIBUTED, PREVSLICE, SYNCUPDATE, PORT, SONGLIST, NUMOFTIMES)
   
   if configerror:   # error reading config.xml
      my_config.error = True
      return my_config

   if treeroot.find('Director'):
      p = treeroot.find('Director')

      #########################################
      # Read DirectorAddr attribute           #
      #########################################
      try:
         DIRECTOR_ADDR = p.find('DirectorAddr').text
      except:
         print("Could not find DirectorAddr attribute in config.xml")
         configerror = True
         DIRECTOR_ADDR = ""

   if treeroot.find('Controller_Section'):
      p = treeroot.find('Controller_Section')
      
      #########################################
      # Read CtrlIPAddr attribute             #
      #########################################
      try:
         ctrlipaddress = p.find('CtrlIPAddr').text
      except:
         print("Could not find CtrlIPAddr attribute in controller section of config.xml")
         my_config.error = True
         return my_config

      #########################################
      # Read Controller_Index attribute       #
      #########################################
      try:
         ctrlindex = int(p.find('Controller_Index').text)
      except:
         print("Could not find Controller_Index attribute in controller section of config.xml")
         my_config.error = True
         return my_config

      ##############################################################################
      # If is_director then check to see if ctrl IP addr is in directors ctrl list #
      # If not, then add controller to controller list                             #
      ##############################################################################
      if my_config.is_director:
         found = False
         for c in my_config.ctrl_list:
            if c.ip_addr == ctrlipaddress:
               found = True
               my_ctrl = c
               break
         if not found:
            print ("In controller section of config.xml, ctrl_IP_Addr ", ctrlipaddress,
                   " is not in director's controller list ", DIRECTOR_CTRL_ADDR)
            my_config.error = True
            return my_config
      else:    # not director - add ctrl to ctrl_list
         my_config.ctrl_list.append(controller.Controller(ctrlipaddress, ctrlindex))
         my_ctrl = my_config.ctrl_list[0]
      print("\n\nI am controller with index: ", my_ctrl.index,
            " with address ", my_ctrl.ip_addr)
      my_ctrl.is_local = True

      ###############################
      # Read sub_controllers        #
      ###############################
      if p.find('Sub_Ctrl_List'):
         p2 = p.find('Sub_Ctrl_List')
         start_channel = 1
         for child in p2:

            #####################################
            #  Read in data for shift sub_ctrl  #
            #####################################
            if child.tag == 'Shift':
                              
               ########################################
               # read shift sub_ctrl num_ch attribute #
               ########################################
               try:
                  numch = int(child.find('Num_Ch').text)
               except:
                  print("Shift sub_controller does not have a Num_Ch attribute")
                  my_config.error = True
                  return my_config

               ##########################################
               # read shift sub_ctrl data_pin attribute #
               ##########################################
               try:
                  datapin = int(child.find('Data_Pin').text)
               except:
                  print("Shift sub_controller does not have a Data_Pin attribute")
                  my_config.error = True
                  return my_config

               ###########################################
               # read shift sub_ctrl clock_pin attribute #
               ###########################################
               try:
                  clockpin = int(child.find('Clock_Pin').text)
               except:
                  print("Shift sub_controller does not have a Clock_Pin attribute")
                  my_config.error = True
                  return my_config

               ###########################################
               # read shift sub_ctrl latch_pin attribute #
               ###########################################
               try:
                  latchpin = int(child.find('Latch_Pin').text)
               except:
                  print("Shift sub_controller does not have a Latch_Pin attribute")
                  my_config.error = True
                  return my_config
               my_ctrl.add_shift_sub(act_sub_ctrl, start_channel, numch,
                                     datapin, clockpin, latchpin)
               start_channel += numch
               continue   # goto next sub_ctrl

            #####################################
            #  Read in data for pixel sub_ctrl  #
            #####################################
            if child.tag == 'Pixel':

               ########################################
               # read pixel sub_ctrl num_ch attribute #
               ########################################
               try:
                  numch = int(child.find('Num_Ch').text)
               except:
                  print("Pixel sub_controller does not have a Num_Ch attribute")
                  my_config.error = True
                  return my_config

               #################################
               # read pixel USB_Port attribute #
               #################################
               try:
                  usb_port = child.find('USB_Port').text
               except:
                  print("Pixel sub_controller does not have a USB_Port attribute")
                  my_config.error = True
                  return my_config

               #######################################
               # read pixel USB_Serial_Num attribute #
               #######################################
               try:
                  usb_serial_num = child.find('USB_Serial_Num').text
               except:
                  print("Pixel sub_controller does not have a USB_Serial_Num attribute")
                  my_config.error = True
                  return my_config

               usbconn = get_serial_info(usb_port, usb_serial_num)
               if not usbconn:    #serial number does not match or something else wrong with device connected to USB port
                  my_config.error = True
                  return my_config

               my_ctrl.add_pixel_sub(act_sub_ctrl, start_channel, numch, usbconn, usb_port)
               start_channel += numch
               continue   # goto next sub_ctrl

            ####################################
            # Sub_ctrl not pixel or shift type #
            ####################################
            print ("Invalid type of sub_controller in controller section in config.xml")
            print (child.tag)
            my_config.error = True
            return my_config
 
      else:
         print("Sub_Ctrl_List was not found in Controller section in config.xml")
         my_config.error = True
         return my_config
 
   return my_config
