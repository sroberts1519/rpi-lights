#!/user/bin/env python3

class Fseq_File:
   def __init__(self, filename):
      self.filename = filename
      self.file = open(self.filename, 'rb')
      self.len = self.get_length()
      self.ch_start = 0
      self.slicesize = 0
      self.audioformat = None
      self.audiofile = ""
      self.sliceoffset = 0   #sliceoffset only used by director
      self.samplerate = 0    #sample rate is only used by non-director in distributed mode

   def move_to_end(self):
      self.file.seek(0, 2)

   def move_to_start(self):
      self.file.seek(0, 0)

   def move_to_ch_start(self):
      self.file.seek(self.ch_start)      # removed the -1 because it was starting in wrong place

   def get_length(self):
      pos = self.file.tell()   #record where we started
      self.move_to_end()
      filesize = self.file.tell()
      self.file.seek(0, pos)   #return back to where we started
      return filesize

   def read_header(self, is_director, distributed = None, samplerate = None, xmlfilename= None):
      self.move_to_start()
      # byte 0-3 should be FSEQ
      if self.file.read(4).decode('UTF-8') != "FSEQ":
         print ("ERROR!!!!   ", self.filename, "has an invalid file format.  Must start with FSEQ")
         return False

      # byte 4 is start of channel streams
      self.ch_start = ord(self.file.read(1))

      # byte 10-13 is slice size
      self.file.seek(10)
      self.slicesize = ord(self.file.read(1)) + (ord(self.file.read(1)) << 8) + (ord(self.file.read(1)) << 16) + (ord(self.file.read(1)) << 24) 

      # byte 18-19 is sampling speed
      self.file.seek(18)
      self.samplerate = ord(self.file.read(1))+(ord(self.file.read(1))<<8)
      if is_director and self.samplerate != samplerate:
         print ("ERROR!!! Sample rate in ", xmlfilename, " does not match ", self.filename)
         return False

      # byte 30 audio file format ?
      # may need to use repr instead of str
      self.file.seek(30)
      self.audioformat = self.file.read(2).decode('UTF-8')

      # byte 33 to n contains audio filename
      self.file.seek(33)
      c = self.file.read(1).decode('UTF-8')
      while ord(c) != 0:
         self.audiofile += str(c)
         c = self.file.read(1).decode('UTF-8')
      return True
