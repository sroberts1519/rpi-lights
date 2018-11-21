#!/user/bin/env python3
import socket
import controller

#dir_ctrl_list[0] - Index
#dir_ctrl_list[1] - Name
#dir_ctrl_list[2] - StartCh
#dir_ctrl_list[3] - NumCh

def attach_ctrls(dir_ctrl_list, my_config):
   # dir_ctrl_list is generated from xml file

   ####################################
   #   Attach controllers to director #
   ####################################
   print("Verifying controllers with director's song's xml file")
   for x in dir_ctrl_list:
      #find controller in ctrl_list
      found = False
      for c in my_config.ctrl_list:
         if x[0] == c.index:
            found = True
            break  #found controller in dir_ctrl_list
      if not found:
         print("Controller index: ",x[0], "in *_Network.xml was not found in Director's config.xml ctroller list")
         return False
      if c.is_local:
         if c.tot_num_ch != x[3]:
            print("My number of channels from (config.xml: ", c.tot_num_ch, ")")
            print("       does not match network.xml (", x[3], ")")
            return False
         print("Verified controller with index ", c.index, " as self and config matches song's xml file")
      else:    #controller not us - verify remote controller configuration
         if int(c.tot_num_ch) != x[3]:
            print("Controller: ", c.index, " number of channels in it's config.xml (", c.tot_num_ch, ")")
            print("                does not match director's network.xml number of channels (", x[3], ")")
            return False
         print("Verified controller ", c.index, " with IP address ", c.ip_addr, "matches song's xml file")
         #end remote controller

      c.name = x[1]
      c.start_ch = x[2]
      c.available = True
      c.error_count = 0

   ###############################################################
   # Make sure all controllers in config.xml:director registered #
   # from search through network.xml controller index's          #
   ###############################################################
   # dont think this is necessary - not having it allows for physical
   #     controllers that may not be in the current song xml file
   #for c in my_config.ctrl_list:
   #   if not c.available:
   #      print("Director's config.xml controllers list, controller index: ", c.index,
   #            "did not register.  It is not in network.xml controller list")
   #      c.error = True
   #      my_config.error = True
   #      return
   print("All controllers listed in *_Network.xml file verified to controllers configuration\n")
   return True
