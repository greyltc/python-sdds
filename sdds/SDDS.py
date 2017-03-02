from . import eprint
import gzip
import f90nml
import io

class SDDS:
  def __del__(self):
    # close any open files
    try:
      close (self.fp)
    except:
      pass
    try:
      close (self.gzfp)
    except:
      pass

  def __init__(self, fileName=None):
    self.fileName = fileName
    self.description = ["", ""]
    self.gzipped = None # is the underlying file gzipped?
    self.nPages = None # number of data pages
    self.tableCols = None # aspects of the columns in the table (None if no table)
    if fileName is not None:
      self.fp = open(self.fileName,'rb') # open the file for reading
      try:
        first4 = self.fp.read(4).decode('utf-8') # let's inspect just the first 4 bytes
      except:
        first4 = ''
      self.fp.seek(0) # reset pointer
      if first4 != 'SDDS':
        #self.gzfp = copy.copy(self.fp) # make a copy of the file pointer for gzip mode reading
        self.gzfp = gzip.GzipFile(fileobj=self.fp) # try reading the file as gzip data
        try:
          first4 = self.gzfp.read(4).decode('utf-8') # now does it look like SDDS?
        except:
          first4 = ''
        self.gzfp.seek(0)
        if first4 != 'SDDS':
          eprint('This file does not start with "SDDS"')
          return
        else:
          self.wfp = self.gzfp # set working file pointer
          self.gzipped = True
      else:
        self.wfp = self.fp # set working file pointer
        self.gzipped = False
      
      versionLine = self.wfp.readline().rstrip()
      self.version = int(versionLine[4:])
      
      if self.version != 1: # do we have version 1?
        eprint('Unsupported SDDS format version:', versionLine)
        return
      
      # switch to text mode with utf-8 encoding
      position = self.wfp.tell()
      try: 
        rawStream = self.wfp.detach() #this fails when we're reading a gzip'd file
        self.wfp = io.TextIOWrapper(rawStream,'utf-8')
      except:
        self.fp.seek(0)
        self.wfp = gzip.open(self.fp, mode='rt', encoding='utf-8')
      
      self.wfp.seek(position)
      
      # parse the header line with f90nml
      parser = f90nml.Parser()
      headerNml = parser.read(self.wfp)
      #headerNml = f90nml.read(self.wfp)
      
      for commandSet in headerNml.items():
        command = commandSet[0]
        parameters = commandSet[1]
        if command == 'column':
          self.tableCols = []
          for column in parameters:
            tableCol = {}
            for (attribute,value) in column.items():
              tableCol[attribute] = value
            self.tableCols.append(tableCol)
        elif command == 'include':
          eprint('Error: include command not yet supported!')
          return
        elif command == 'data':
          for (attribute,value) in parameters.items():
            print(attribute, '=', value)
            if attribute.lower == 'mode' and value.lower != 'ascii':
              eprint('Error:', value.lower, 'mode data not yet supported!')
              return
        else:
          eprint('Unrecognized command in header: ' + command)
      
      #TODO figure out how to get back to the end of the header
      print(self.wfp.read())