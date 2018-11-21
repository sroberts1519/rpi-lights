#!/user/bin/env python3

######################
# Read the .xml file #
######################

#dir_ctrl_list[0] - Index
#dir_ctrl_list[1] - Name
#dir_ctrl_list[2] - StartCh
#dir_ctrl_list[3] - NumCh

import xml.etree.ElementTree

class read_xml:
   def __init__(self, xml_filename, ctrl_list):
      self.error = False
      treeroot = xml.etree.ElementTree.parse(xml_filename).getroot()
      self.samplerate = int(treeroot.find('Resolution').text)
      self.seqfilename = treeroot.find('OutFile').text
      d = treeroot.find('Duration').text.split(':')   # ['hh', 'mm', 'sec.xxxxxx']
      #calculate duration in msec
      self.duration = int(float(d[2]))*1000 + int(d[1])*60*1000 + int(d[0])*3600*100
      self.filename = xml_filename
  
      p = treeroot.find('Network')
      self.dir_ctrl_list = []
      for c in p.findall('Controller'):
         self.dir_ctrl_list.append((int(c.find('Index').text), c.find('Name').text,
                                   int(c.find('StartChan').text)-1, int(c.find('Channels').text)))

      # check to make sure each controller listed in xml_file (by index)
      # is in ctrl_list (my_config.ctrl_list).
      # This is ensure that the director's config file listing
      # for director's attributes match xml_file (index)
      for i in self.dir_ctrl_list:
         found = False
         for y in ctrl_list:
            if i[0] == y.index:   # i[0] is index num
               found = True
               break
         if not found:
            print(xml_filename, " controller index ", i[0],
                  " not found in config.xml director attributes")
            self.error = True
