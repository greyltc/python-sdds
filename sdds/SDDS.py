from . import eprint
import gzip
import f90nml
import io
import re

class SDDS:
  def __init__(self, fileName=None):
    self.description = ["", ""]
    self.version = None # SDDS format version
    self.gzipped = None # is the underlying file gzipped?
    self.nPages = None # number of data pages
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
      
      partitioned = f.partition(b'\n!') # split out the header
      header = partitioned[0] 
      headerLines = header.splitlines() # split the header into lines
      del headerLines[0] # we already checked that this is 'SDDS1'
      
      # parse each header line using f90nml
      nmlStream =  io.StringIO() # we'll write our header lines to this file-like object so that f90nml can read them
      for hLine in headerLines:
        string = hLine.decode("utf-8").replace('=%',"='%'") # hack to fix a bug in f90nml, see https://github.com/marshallward/f90nml/issues/42
        nmlStream.write(string)
        nmlStream.truncate() # delete any previous longer line leftover
        nmlStream.seek(0) # go back to the start of the file to get ready to read
        nameList = f90nml.read(nmlStream) # parse the header line with f90nml
        nmlStream.seek(0) # get ready to write the next header line
        print('Header Row: ' + str(nameList))
      
      dataPages = b'!' + partitioned[2] # reattach the !
      dataPages = re.split(b'! page number [0-9]*\n', dataPages) # split up each page
      del dataPages[0] # remove the empty index from re.split
      self.nPages = len(dataPages)
      
      for page in dataPages:
        print('Data Page: ' + str(page))