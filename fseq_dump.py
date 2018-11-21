#!/user/bin/env python3

# Binary File Dump

import signal
import sys
import fseq

def ctrl_c_handler(signal, frame):
   print ("\nYou pressed Ctrl+C!")
   exit()

signal.signal(signal.SIGINT, ctrl_c_handler)

#get fseq filename to open and read
if len(sys.argv) < 2:
   print ("Error!!!!   Format:  python3 dump.py <filename>.fseq")
   exit()

try:
   fseqfile = fseq.Fseq_File(sys.argv[1])
except OSError:
   print("Error opening sequence file:", sys.argv[1])
   exit()

if not fseqfile.read_header(False):    #False = not director - dont care
   exit()

#get slice size
fseqfile.file.seek(10)
slicesize = ord(fseqfile.file.read(1)) + (ord(fseqfile.file.read(1)) << 8) + (ord(fseqfile.file.read(1)) << 16) + (ord(fseqfile.file.read(1)) << 24) 
print("Slice size:", slicesize)

n = int(input("Enter number of columns: "))  

fseqfile.move_to_start()
print("\nHeader Bytes")
print("------------")
for i in range(0, fseqfile.ch_start-1):
   byte = fseqfile.file.read(1)
   print(str(ord(byte)).rjust(3), end = ' ')
print("\n\nHeader Decoded")
print("--------------")
print("File type:  FSEQ")
print("Channel start:", fseqfile.ch_start)
print("Slice size:", slicesize)
print("Sample rate:", fseqfile.samplerate)
print("Audio Format:", fseqfile.audioformat)
print("Audio file:", fseqfile.audiofile)

print("\n\nChannel Numbers")

for i in range(1, n+1):
   print(str(i).rjust(3), end = ' ')

print("\n","-"*4*n)
a = 0
fseqfile.move_to_ch_start()
byte = fseqfile.file.read(1)
while byte:
   print(str(ord(byte)).rjust(3), end = ' ')
   a += 1
   if a == n:
      print(" ")
      a = 0
   byte = fseqfile.file.read(1)
exit()

