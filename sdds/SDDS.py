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
    self.mode = 'binary'
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
      
      class MyParser(f90nml.Parser):
        def __init__(self):
          self.inNml = False
          self.endThis = False
          self.inParameterCmd = False
          self.needDataCmd = False
          self.inDataCmd = False
          self.fixedValueParam = False
          self.lastHeaderLine = 0
          super(MyParser, self).__init__()
        def __setattr__(self, k, v): 
          super(MyParser, self).__setattr__(k, v)
          if k == 'prior_token':
            #print(self.prior_token)
            #print(self.token)
            #print('')
            if not self.inNml and self.prior_token in ('&', '$') and self.token.lower() in ('description', 'column', 'parameter', 'array', 'include', 'data'): # we saw a start indicator
                self.inNml = True
                if self.token.lower() in ('array', 'column'):
                  self.needDataCmd = True
                if self.token.lower() == 'parameter':
                  self.inParameterCmd = True
                if self.token.lower() == 'data':
                  self.inDataCmd = True                
            elif self.inParameterCmd and self.token.tolower() == 'fixed_value':
              self.fixedValueParam = True
            elif self.inNml and self.prior_token in ('&', '$', '/'): # we saw an end terminator
              self.inNml = False
              if self.inParameterCmd:
                self.inParameterCmd = False
                if self.fixedValueParam == False:
                  self.needDataCmd = True
                else:
                  self.fixedValueParam = False
                  
            # we're done if we saw an end terminator while in a data command
            if (self.inDataCmd == True) and self.token in ('&', '$', '/'): 
              self.lastHeaderLine = self.tokens.lineno
              self.endThis = True
            
            if not self.inNml and self.token in ('end', None):
              pass
            elif not self.inNml and self.token not in ('&', '$') and not self.needDataCmd:
              # TODO: double check this termination case 
              self.lastHeaderLine = self.tokens.lineno
              self.endThis = True
            
            
        def update_tokens(self, *args, **kwargs):
          if self.endThis == False:
            super(MyParser, self).update_tokens(*args, **kwargs)
          else:
            raise StopIteration
            
      
      # parse the header line with f90nml
      #parser = f90nml.Parser()
      parser = MyParser()
      #headerNml = parser.read(self.wfp)
      storage = io.StringIO()
      patch_nml = {'data': {'somemagic': "deadbeef"}}
      headerNml = parser.read(self.wfp)
      #headerNml = f90nml.read(self.wfp)
      
      self.nHeaderLines = parser.lastHeaderLine + 1
      
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
            if attribute.lower == 'mode' and value.lower != 'ascii':
              eprint('Error:', value.lower, 'mode data not yet supported!')
              return
            else:
              self.mode = 'ascii'
              
        else:
          eprint('Unrecognized command in header: ' + command)
      
      self.wfp.seek(0)
      self.header = ''
      for i in range(self.nHeaderLines):
        self.header = self.header + self.wfp.readline()
      self.dataPages = self.wfp.read()