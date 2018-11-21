#!/user/bin/env python3
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

print(getrevision())
print(pi_version[getrevision()])
