#!/user/bin/env python3

# Christmas Light Director Version 2
# Raspberry Pi is the controller

# config.xml director section will list controllers as:
#   - CtrlIPList
#   - CtrlIndexList
#
# read_config will create a list of controllers (my_config.ctrl_list)
#    and store address and index from above listed information
#        - my_config.ctrl_list[x].ip_address
#        - my_config.ctrl_list[x].index
#
# read_xml (network.xml) will: 
#    - read the network.xml file and store it in the xml_file class
#    - check to make sure all controllers listed in network.xml
#           (by index) are in my_config.ctrl_list
#
# During attach_controllers loop through controllers in my_config.ctrl_list:
#   - if self:
#       * check to make sure my_config.ctrl_list[self].num channels matches network.xml num channels
#       * update info as needed and mark as attached
#   - if remote controller:
#       * request config info from remote controller by ip address
#       * check to make sure it's reported index is same as
#             my_config.ctrl_list[x].index
#       * check reported IP address
#       * check reported number channels vs xml_file

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

###########################################################
#  prev slice optimization
#  the check (if statement) on the director with 24 channels took approx. 10 to 15 microseconds
#  on the remote controller (distributed = yes) with 24 shift and 30 pixel took appox. 8 to 9 microseconds

import time
import pygame
import signal
import sys
import socket
import serial
import controller
import read_xml
import read_config
import dir_module
import fseq

def cleanexit():
   if my_config.clean_exit:
      exit()
   print ("\nExiting cleanly")
   time.sleep(0.2)
   if (fseqfile):
      fseqfile.file.close()
   if my_config.is_director:
      for c in my_config.ctrl_list:
        c.close()
   else:   #not director, check to see if self is a controller and close out controller
      try:
         my_config.ctrl_list[0].close()      #close self
         sock.close()     # server - close socket
      except:
         print("Self has not been established as a controller yet - no need to close")
      
   my_config.clean_exit = True
   exit()

def ctrl_c_handler(signal, frame):
   print ("\nYou pressed Ctrl+C!")
   cleanexit()

signal.signal(signal.SIGINT, ctrl_c_handler)   #set ctrl-c handler for clean exit
fseqfile = None

try:
   my_config = read_config.readconfig(True)    #True = activate sub_ctrlers
except OSError:
   print("Error reading config.xml")
   cleanexit()
if my_config.error:
   print("Error with validating the configuration in config.xml\n   or other general error while reading config.xml.")
   cleanexit()

##########################################
#   DIRECTOR Code                        #
##########################################
if my_config.is_director:
   print("\nI am director with address: ", my_config.director_addr, " using port: ", my_config.port)

   if my_config.prevslice:
      print("Previous Slice mode")
   else:
      print("Non-Previous Slice mode")
   if my_config.distributed:
      print("Distributed with sync time of ", my_config.syncupdate, "msec")
   else:
      print("Non-Distributed mode")

   # open IP connection to all remote controllers and get remote controllers config
   for c in my_config.ctrl_list:
      if not c.is_local:
         if not c.open_conn(my_config.port):
            cleanexit()
   print("\nAll controllers listed in the director's controller list responded and are connected")
              
   loopcount = 0
   while loopcount < my_config.numoftimes:
      for songname in my_config.songlist:
         print("\n***********************************")
         print("Playing: ", songname)
         print("***********************************\n")
         try:
            xml_file = read_xml.read_xml(songname, my_config.ctrl_list)
         except:
            print("Error reading ", songname, " xml file")
            cleanexit()
         if xml_file.error:
            cleanexit()

         # Verify all controllers match director's *_Network.xml file
         #   Also each controller in *_Network.xml is marked as available
         #          in my_config.ctrl_list
         if not dir_module.attach_ctrls(xml_file.dir_ctrl_list, my_config):
            cleanexit()

         for c in my_config.ctrl_list:       # calculate slicesize from director:controllers_list
            if c.available:
               my_config.slicesize += c.tot_num_ch

         #################################
         # Open fseqfile and read header #
         #################################
         try:
            fseqfile = fseq.Fseq_File(xml_file.seqfilename)
         except OSError:
            print("Error opening sequence file ", xml_file.seqfilename)
            cleanexit()
         if not fseqfile.read_header(my_config.is_director, my_config.distributed,
                                     xml_file.samplerate, xml_file.filename):
            cleanexit()
         #############################################
         # calculate slice offset if not distributed #
         # if distributed, then there is no offset   #
         #############################################
         if not my_config.distributed:
            fseqfile.sliceoffset = fseqfile.slicesize - my_config.slicesize

         #####################################
         # print slicesize and offset values #
         #####################################
         print("LightShow slice info")
         if my_config.distributed:
            print("My Config total slicesize:", my_config.slicesize, "fseqslicesize: ", fseqfile.slicesize)
            mysize = 0
            for c in my_config.ctrl_list:
               if c.is_local:
                  mysize += c.tot_num_ch
            if not mysize == fseqfile.slicesize:
               print("FSEQ file slice size:", fseqfile.slicesize, "does not match my controller slice size:", mysize)
               cleanexit()
            print("My local controller total slice size:", mysize)
           
         else:    # not distributed
            print("My Config slicesize:", my_config.slicesize, "fseqslicesize: ", fseqfile.slicesize, "offset:", fseqfile.sliceoffset)             

         fseqfile.move_to_ch_start()    # move to start of channel info

         ###########################################################
         #  If distributed:                                        #
         #      Tell remote controllers to start playing next song #
         ###########################################################
         if my_config.distributed:         # signal all controllers to start playing song
            next_sync = my_config.syncupdate
            print("Signaling all controllers to play:", xml_file.filename)
            for c in my_config.ctrl_list:
               if not c.is_local and c.available:   # controller not this device
                  c.socket.settimeout(0.1)     # for some reason there is a delay for this communicaton
                  try:
                     c.socket.sendall(b'PLAY ' + xml_file.seqfilename.split('.')[0].encode()
                                      + str(c.index).encode() + b'.'
                                      + xml_file.seqfilename.split('.')[1].encode())
                     message = c.socket.recv(16)
                  except:
                     print("Error sending PLAY command to controller index:", c.index, "IP address:", c.ip_addr)
                     print("Error:", sys.exc_info()[0])
                     cleanexit()
                  if not message.decode() == "PLAYACK":
                     print ("Controller:", c.index, "IP addr:", c.ip_addr, "did not send us correct acknowledgement to our PLAY command")
                     cleanexit()
                  c.socket.settimeout(0.05)   # restore timeout back to standard 50 msec

         #################################
         #  Director start playing mp3   #
         #################################
         pygame.mixer.init()
         pygame.mixer.music.load(fseqfile.audiofile)
         pygame.mixer.music.play()
         while pygame.mixer.music.get_busy() == False:   #ensure song has started playback
            time.sleep(0.01)
         pygame.mixer.music.set_volume(1)

         nextevent = 500
         while pygame.mixer.music.get_pos() <= xml_file.duration:
            while pygame.mixer.music.get_pos() < nextevent:
               time.sleep(0.01)
            for c in my_config.ctrl_list:
               if my_config.distributed and not c.is_local:
                  continue
               c.curslice = fseqfile.file.read(c.tot_num_ch)
               if my_config.prevslice:           # using prev slice optimization - keep track of prev slice
                  if c.curslice == c.prev:      # channels did not change from prev slice.  Move on
                     continue
                  c.prev = c.curslice
               if c.outputtolights():   #if error occured outputing to controller the, exit
                  cleanexit()
            nextevent += xml_file.samplerate
            if fseqfile.file.tell() > fseqfile.len:  #ensure dont read past end of fseqfile
               print("Error, trying to read past end of ", fseqfile.filename)
            # There is no offset if distributed
            #     - i.e. the offset bytes are taken when fseq file was parsed
            if not my_config.distributed:    
               fseqfile.file.read(fseqfile.sliceoffset)
            t = pygame.mixer.music.get_pos()
            if my_config.distributed and t >= next_sync:      #send sync message
               for c in my_config.ctrl_list:
                  if not c.is_local:
                     # send sync message to remote controller
                     if c.send_sync_msg(t):
                        cleanexit()
               next_sync += my_config.syncupdate
         fseqfile.file.close()

         #######################
         # End of song cleanup #
         #######################
         time.sleep(2)     # pause for a sec just to make sure all controllers are done playing the song
         print("\nDone playing song", songname)
         my_config.slicesize = 0
         for c in my_config.ctrl_list:
            if not c.sig_end_of_song():     # signal end of song = True
               cleanexit()
         time.sleep(5)
      loopcount += 1
   print("\n********************")
   print("End of light show")
   for c in my_config.ctrl_list:
      if not c.is_local:
         if not c.sig_end_of_show():
            cleanexit()
   cleanexit()

##########################
#   Not Director Code    #
##########################
else:     # not the director
   print("\nI am not a director")
   if my_config.distributed:
      if my_config.prevslice:
         print("\nPrevious Slice Mode")
      else:
         print("\nNon-Previous Slice Mode")
   if my_config.distributed:
      print("Distributed mode\n")
   else:
      print("Non-Distributed mode\n")

   ################################################
   #   Attach to director  (controller is server) #
   ################################################
   my_ctrl = my_config.ctrl_list[0]     #not director - my controller is first in controller list
   sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   sock.bind((my_ctrl.ip_addr, my_config.port))   #self is server

   ###############################################
   # Establish TCP/IP connection with director   #
   ###############################################
   print("Listening for Director (IP address: ", my_config.director_addr, ") to connect")
   sock.listen(1)
   my_ctrl.socket, addr = sock.accept()   
   
   print ("Connected to director: ", addr[0], " on port: ", addr[1])
   if my_config.director_addr != addr[0]:
      print("Connected to director ", addr, " should have been director ", my_config.director_addr)
      print("Telling director connection was not successful")
      my_ctrl.socket.sendall(b'ERROR')
      #get exit now message from director
      message = my_ctrl.socket.recv(16)
      cleanexit()
   else:
      print("Telling director connection was successful")
      my_ctrl.socket.sendall(b'CONNECTSUCCESS')

   ################################
   # send config info to director #
   ################################
   my_ctrl.socket.settimeout(1)    # director may be singalling many controllers - wait a few seconds
   try:
      message = my_ctrl.socket.recv(16)
   except:
      print ("Timed out while waiting for director to request configuration info from me")
      cleanexit()
   my_ctrl.socket.settimeout(0.01)   # connection established - should never be long for communication now
   if not message.decode() == "SENDCONFIG":
      print ("Director did not send us correct message asking for our configuration")
      cleanexit()
   print("Sending config info to director to verify with Director's song's xml file")
   message = "address " + my_ctrl.ip_addr + " index " + str(my_ctrl.index) + " numch " + str(my_ctrl.tot_num_ch)
   my_ctrl.socket.sendall(message.encode())     #respond back to director and give config.xml info
   try:
      message = my_ctrl.socket.recv(16)
   except:
      print("Timed out while waiting for director to acknowledge our configuration")
      cleanexit()
   if not message.decode() == "CONFIGACK":
      print ("Director did not send us correct acknowledgement to our configuration")
      cleanexit()
      
   ###################################
   # Start main loop of non-director #
   ###################################
   if not my_config.distributed:
      my_ctrl.socket.settimeout(120)        # in non-distributed, with prevslice, could be several seconds between messages 
   while True:

      ##########################
      #                        #
      #  Non-Distributed Mode  #
      #                        #
      ##########################
      while not my_config.distributed:
         try:
            my_ctrl.curslice = my_ctrl.socket.recv(my_ctrl.tot_num_ch + 9)     # +9 for START and END
         except:
            print("Error receiving packet from director")
            print("Error: ", sys.exc_info()[0])
            cleanexit()
         if not my_ctrl.curslice:
            print("Lost connection with Director.")
            cleanexit()
         if len(my_ctrl.curslice) == 7 and my_ctrl.curslice.decode() == "EXITNOW":
            print("\nDirector told us to exit")
            try:
               my_ctrl.socket.sendall(b'EXITNOWACK')
            except:
               print("Error sending EXITNOW acknowledgement to director")
               print("Error: ", sys.exc_info()[0])
            cleanexit()
         if len(my_ctrl.curslice) == 9 and my_ctrl.curslice.decode() == "ENDOFSONG":
            print("\nDirector told us end of song")
            try:
               my_ctrl.socket.sendall(b'ENDOFSONGACK')
            except:
               print("Error sending ENDOFSONG acknowledgement to director")
               print("Error: ", sys.exc_info()[0])
               cleanexit()
            break
         if len(my_ctrl.curslice) == 9 and my_ctrl.curslice.decode() == "ENDOFSHOW":
            print("\nDirector told us end of show")
            my_ctrl.lights_off()
            try:
               my_ctrl.socket.sendall(b'ENDOFSHOWACK')
            except:
               print("Error sending ENDOFSHOW acknowledgement to director")
               print("Error: ", sys.exc_info()[0])
               cleanexit() 
            break
         if my_ctrl.check_start_end():
            my_ctrl.outputtolights()

      ######################
      #                    #
      #  Distributed Mode  #
      #                    #
      ######################
      while my_config.distributed:
         # Get name of file to be played from director
         my_ctrl.socket.settimeout(10)   #could be a few seconds before director tells us what song to play
         try:
            message = my_ctrl.socket.recv(32)
         except:
            print("Error receiving message from director")
            print("Error: ", sys.exc_info()[0])
            cleanexit()
         if len(message) == 7 and message.decode() == "EXITNOW":
            print("\nDirector told us to exit")
            try:
               my_ctrl.socket.sendall(b'EXITNOWACK')
            except:
               print("Error sending EXITNOW acknowledgement to director")
               print("Error: ", sys.exc_info()[0])
            cleanexit()
         if len(message) == 9 and message.decode() == "ENDOFSONG":
            print("\nDirector told us end of song")
            try:
               my_ctrl.socket.sendall(b'ENDOFSONGACK')
            except:
               print("Error sending ENDOFSONG acknowledgement to director")
               print("Error: ", sys.exc_info()[0])
               cleanexit()
            break
         if len(message) == 9 and message.decode() == "ENDOFSHOW":
            print("\nDirector told us end of show")
            my_ctrl.lights_off()
            try:
               my_ctrl.socket.sendall(b'ENDOFSHOWACK')
            except:
               print("Error sending ENDOFSHOW acknowledgement to director")
               print("Error: ", sys.exc_info()[0])
               cleanexit() 
            break
         if not message[0:4].decode() == "PLAY":
            print("Did not get correct command from Director")
            cleanexit()
         my_ctrl.socket.settimeout(0.01)
         try:
            my_ctrl.socket.sendall(b'PLAYACK')
         except:
            print("Error sending PLAY acknowledgement to director")
            print("Error: ", sys.exc_info()[0])
            cleanexit()
         seqfilename = message.decode().split(' ')[1]
         print("Playing: ", seqfilename)
         try:
            fseqfile = fseq.Fseq_File(seqfilename)
         except OSError:
            print("Error opening sequence file ", seqfilename)
            cleanexit()        
         if not fseqfile.read_header(my_config.is_director, my_config.distributed):
            cleanexit()

         ###################
         # print slicesize #
         ###################
         if not fseqfile.slicesize == my_ctrl.tot_num_ch:
            print("FSEQ file slice size:", fseqfile.slicesize, "does not match my controller slice size:", my_ctrl.tot_num_ch)
            cleanexit()
         print("My Config slicesize:", my_ctrl.tot_num_ch, "fseqslicesize: ", fseqfile.slicesize,)

         fseqfile.move_to_ch_start()    # move to start of channel info
         start_time = int(time.perf_counter()*1000)    # start time of song in msec
         next_sync = int(time.perf_counter()*1000) + my_config.syncupdate + 100    #100 msec is buffer
         nextevent = start_time + 500
         offset = 0

         ##################################
         #  Main loop of Distributed mode #
         ##################################
         while fseqfile.file.tell() < fseqfile.len:
            if int(time.perf_counter()*1000) - offset > nextevent:
               
            #while int(time.perf_counter()*1000) - offset < nextevent:
            #   time.sleep(0.01)
               my_ctrl.curslice = fseqfile.file.read(my_ctrl.tot_num_ch)
               if my_config.prevslice:
                  if my_ctrl.curslice != my_ctrl.prev:
                     if my_ctrl.outputtolights():
                        cleanexit()
                  my_ctrl.prev = my_ctrl.curslice
               else:
                  if my_ctrl.outputtolights():
                     cleanexit()
               nextevent += fseqfile.samplerate

            if time.perf_counter()*1000 > next_sync:
               print("\nDid not recieve sync message from director in required amount of time.")
               print("Must have lost communication with director")
               cleanexit()
            try:
               message = my_ctrl.socket.recv(32)
            except:           # no sync message from director - timed out
               continue       # continue with loop to play song
            else:  
               if not message:
                  print("Received a blank message.")
                  break
               #check message this way in case other char is on front of message
               if message[len(message)-7:].decode() == "EXITNOW":
                  print("\nDirector told us to exit")
                  try:
                     my_ctrl.socket.sendall(b'EXITNOWACK')
                  except:
                     print("Error sending EXITNOW acknowledgement to director")
                     print("Error: ", sys.exc_info()[0])
                  cleanexit()
               if len(my_ctrl.curslice) == 9 and my_ctrl.curslice.decode() == "ENDOFSONG":
                  print("\nDirector told us end of song but we are not done playing song")
                  cleanexit()
               if message[0:4] == b'SYNC' and message[len(message)-3:] == b'END':
                  #try:
                  my_ctrl.socket.sendall(b'RECEIVED')
                  #except:
                  #   print("Error sending SYNC acknowledgement to director")
                  #   print("Error: ", sys.exc_info()[0])
                  #   cleanexit()
                  offset = int(time.perf_counter()*1000) - start_time - int(message[4:-3].decode())
                  #print("Offset: ", offset, " msec")
                  next_sync = int(time.perf_counter()*1000) + my_config.syncupdate + 100   #100 msec is buffer
               else:
                  my_ctrl.socket.sendall(b'FLUSHED')
                  print("Received invalid sync message from director.  Flushing message")
         print("Done playing",seqfilename)
         my_ctrl.lights_off()
         
         

#cleanexit()
   
