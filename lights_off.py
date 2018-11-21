#!/user/bin/env python3

# Turn off all lights on a shift controller
# this is done by calling the clear method in the shifter class

import read_config 

def cleanexit():
   for c in my_config.ctrl_list:
      if c.is_local:
         c.close()
         
try:
   my_config = read_config.readconfig(True)
   #True = activate sub-controllers and turn off all lights
except OSError:
   cleanexit()
cleanexit()
