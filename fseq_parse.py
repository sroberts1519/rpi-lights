#!/user/bin/env python3

# parser to split the Vixen .fseq file into sub *.fseq files for each controller
#
# This program is to be ran on the RPI that is the director.
# I.E. the config.xml file should indicate that this RPI is the director.
#
# This program will read the director's config.xml file and parse/split the *.fseq
# file into sub *.fseq for each controller.  Each controller *.fseq file will
# only contain the channel data that pertains to that controller.
#
# This parser only changes the slice size int the header of the *.fseq file.  That is, the *.mp3
# filename does not change.  The slice size for each fseq file is changed to the correct size for that controller

import signal
import sys
import time
import xml.etree.ElementTree
import read_config
import read_xml
import fseq

class Controller:
   def __init__(self, index, name, startch, numch):
      self.index = index
      self.name = name
      self.start_ch = startch
      self.num_ch = numch
      self.out_file = open(seqfilename.split('.')[0]+str(self.index)+'.'+seqfilename.split('.')[1],'wb')

def cleanexit():
   print ("\nExiting cleanly")
   time.sleep(0.2)
   if fseqfile and fseqfile.file:
      fseqfile.file.close()
   if my_config:
      for c in my_config.ctrl_list:   #close all of the controller output files
         if not c.is_local:            # Director!!!  no out_file so dont try and close
            c.out_file.close()
   if dir_file:                       # Close director file
      dir_file.close()
   exit()

def ctrl_c_handler(signal, frame):
   print ("\nYou pressed Ctrl+C!")
   cleanexit()
 
in_file = None
fseqfile = None
dir_file = None
my_config = None
 
###################################
#         read config.xml         #
#    Make sure we are director    #
###################################
try:
   my_config = read_config.readconfig(False)    #False = do not activate sub_controllers
except OSError:
   print("Error reading config.xml")
   cleanexit()
if not my_config.is_director:
   print("Not Director!!!")
   cleanexit()
#get xml filename to open and read
if len(sys.argv) < 2:
   print ("Error!!!!   Format:  python3 fseq_parse.py <filename>.xml")
   cleanexit()

######################
# Read the .xml file #
######################
try:
   xml_file = read_xml.read_xml(sys.argv[1], my_config.ctrl_list)
except:
   print("Error reading ", sys.argv[1], " xml file")
   cleanexit()
if xml_file.error:
   cleanexit()   

# Update controller.tot_num_ch (from network.xml file) for controllers that is not us
for c in my_config.ctrl_list:
   for x in xml_file.dir_ctrl_list:
      if c.index == x[0]:
         break    #found controller in dir_ctrl_list
   c.tot_num_ch =  x[3]

for c in my_config.ctrl_list:       #    calculate slicesize from controllers_list
   my_config.slicesize += c.tot_num_ch

####################################
# Read the header of the fseq file #
####################################
try:
   fseqfile = fseq.Fseq_File(xml_file.seqfilename)
except OSError:
   print("Error opening sequence file ", xml_file.seqfilename)
   cleanexit()
if not fseqfile.read_header(my_config.is_director, my_config.distributed,
                            xml_file.samplerate, xml_file.filename):
   cleanexit()

###############################
# calculate sliceoffset value #
###############################
fseqfile.sliceoffset = fseqfile.slicesize - my_config.slicesize

print("Light Show slice information")
print("FSEQ file slice size:", fseqfile.slicesize)
for c in my_config.ctrl_list:
   print("Controller index:", c.index, "number of channels:", c.tot_num_ch)
print("Total number of channels of all controllers:", my_config.slicesize)
print("Slice offset value:", fseqfile.sliceoffset)

###############################################################
# Get contents of fseq header to write to parsed *.fseq files #
###############################################################
fseqfile.move_to_start()
buf1 = fseqfile.file.read(10)
fseqfile.file.seek(4, 1)    #read past slice size (4 bytes), from current position (1)
buf2 = fseqfile.file.read(fseqfile.ch_start - 1 - 14)
#buf = buf1 + my_config.slicesize.to_bytes(4, "little") + buf2

################################################################
#                Open all of the controller files              #
# if controller is local dont open because it is director file #
################################################################
for c in my_config.ctrl_list:
   if not c.is_local:
      try:
         c.out_file = open(fseqfile.filename.split('.')[0]+str(c.index)+'.'+fseqfile.filename.split('.')[1],'wb')
      except OSError:
         print("Error opening file ", fseqfile.filename.split('.')[0]+str(c.index)+'.'+fseqfile.filename.split('.')[1])
         cleanexit()

##############################
# Write director file header #
##############################
print("\nWriting director fseq header")
try:
   dir_file = open(fseqfile.filename.split('.')[0]+'D.'+fseqfile.filename.split('.')[1],'wb')
except:
   print("Could not open director ", end="")
   print(fseqfile.filename.split('.')[0]+'D.'+fseqfile.filename.split('.')[1], end="")
   print(" for writing")
#####################################
# Calculate slice size for director #
#####################################
dirsize = 0
for c in my_config.ctrl_list:
   if c.is_local:
      dirsize += c.tot_num_ch
try:
   dir_file.write(buf1 + dirsize.to_bytes(4, "little") + buf2)
except:
   print("Could not write header to ", end="")
   print(fseqfile.filename.split('.')[0]+'D.'+fseqfile.filename.split('.')[1])
   cleanexit()

#####################################
# Write the fseq header file to all #
# of the controller output files    #
# except director                   #
#####################################
print("Writing header to each controller fseq")
for c in my_config.ctrl_list:
   if not c.is_local:
      try:
         c.out_file.write(buf1 + c.tot_num_ch.to_bytes(4, "little") + buf2)
      except:
         print("Could not write header to ", end="")
         print(fseqfile.filename.split('.')[0]+str(c.index)+'.'+fseqfile.filename.split('.')[1])
         cleanexit()

#################################################
# read all of the channel sequence and          #
# parse into the correct controller output file #
#################################################
      
fseqfile.move_to_ch_start()     # move to start of channel info
slice_count = 0
byte_count = 0
print("Processing", end="")
buf = buf1   #just need to assign buf something to get the while loop started
while buf:
   for c in my_config.ctrl_list:
      buf = fseqfile.file.read(c.tot_num_ch)
      byte_count += c.tot_num_ch
      if c.is_local:
         dir_file.write(buf)
      else:
         c.out_file.write(buf)
   print(".",end="")
   slice_count += 1
   fseqfile.file.read(fseqfile.sliceoffset)
   
print("\nProcessed ", slice_count, "slices, and ", byte_count, " bytes.")

cleanexit()
