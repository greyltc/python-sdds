from . import eprint
import gzip

class SDDS:
  def __init__(self, fileName=None):
    self.description = ["", ""]
    self.version = None # SDDS format version
    self.gzipped = None # is the underlying file gzipped?    
    if fileName is not None:
      fp = open(fileName,'rb') # open the file for reading in binary mode
      first5 = fp.read(5) # let's inspect the first 5 bytes
      fp.seek(0) # reset pointer
      if first5[0:4] != b'SDDS':
        gzfp = gzip.GzipFile(fileobj=fp) # maybe it's gzipped
        first5 = gzfp.read(5) # is this really a .sdds file?
        gzfp.seek(0)
        if first5[0:4] != b'SDDS':
          gzfp.close()
          fp.close()
          eprint('This file does not start with "SDDS"')
          return
        else:
          self.gzipped = True
      else:
        self.gzipped = False
      
      self.version = int(chr(first5[4]))
      if self.version != 1: # do we have version 1?
        if self.gzipped:
          gzfp.close()
        fp.close()
        eprint('Unsupported SDDS format version:', self.version)
        return
      
      # probably dumb to store the whole file in RAM...
      if self.gzipped:
        f = gzfp.read()
        gzfp.close()
      else:
        f = fp.read()
      fp.close()
      
      lines = f.split(b'\n')
      for line in lines:
        print (line)