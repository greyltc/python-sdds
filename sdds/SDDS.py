from . import eprint # to print error emessages
import gzip # to handle gzipped files
import f90nml # to parse the header
import io
import numpy as np # for array manipulation
import pandas as pd # for 

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
    
  # switches file access mode to text (assumes utf-8 encoding)
  def switchToTextMode(self):
    if (hasattr(self.wfp,'mode') and self.wfp.mode != 'rt') or (hasattr(self.wfp,'encoding') and self.wfp.encoding != 'utf-8'): 
      position = self.wfp.tell()
      try: 
        rawStream = self.wfp.detach() #this fails when we're reading a gzip'd file
        self.wfp = io.TextIOWrapper(rawStream,'utf-8')
      except:
        self.fp.seek(0)
        self.wfp = gzip.open(self.fp, mode='rt', encoding='utf-8')
      
      self.wfp.seek(position)
      
  # switches file access mode to binary
  def switchToBinMode(self):
    if (hasattr(self.wfp,'mode') and self.wfp.mode in ('rb',1)) or (hasattr(self.wfp,'encoding') and self.wfp.encoding == 'utf-8'): 
      position = self.wfp.tell()
      try: 
        rawStream = self.wfp.detach() #this fails when we're reading a gzip'd file
        self.wfp = io.BufferedReader(rawStream)
      except:
        self.fp.seek(0)
        self.wfp = gzip.open(self.fp, mode='rb')
      
      self.wfp.seek(position)   
    
  # gets a line from the file that's not a comment
  def getLine(self):
    newLine = '!'
    while len(newLine) !=0 and newLine[0] == '!':
      try:
        newLine = self.wfp.readline()
      except:
        eprint("End of file reached")
        raise Exception
    if newLine == '':
      eprint('Got empty line')
      self.__del__()
      raise Exception
    return newLine

  def __init__(self, fileName=None):
    self.fileName = fileName
    self.description = {}
    self.parameters = None
    self.arrays = None
    self.tableCols = None
    self.pageData = [] # this is where we'll put data read from pages
    self.data = {}
    self.data['mode'] = 'binary'
    self.data['additional_header_lines'] = 0
    self.data['lines_per_row'] = 1
    self.data['no_row_counts'] = 0
    self.gzipped = None # is the underlying file gzipped?
    self.nPages = None # number of data pages
    self.nParameters = 0 # number of parameters to be read from data page(s)
    self.nArrays = 0 # number of arrays to be read from data page(s)
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
      
      self.switchToTextMode()
      
      class MyParser(f90nml.Parser):
        def __init__(self):
          self.inNml = False
          self.endThis = False
          self.thisLine = 0
          super(MyParser, self).__init__()
        def __setattr__(self, k, v): 
          super(MyParser, self).__setattr__(k, v)
          if k == ('tokens') and self.tokens != None:
            if '/' not in self.tokens.wordchars:
              self.tokens.wordchars = self.tokens.wordchars+'/' # is possibly dangerous but allows par.twi example
            if '%' not in self.tokens.wordchars:
              self.tokens.wordchars = self.tokens.wordchars+'%' # is possibly dangerous but allows par.twi example            
          elif k == 'prior_token':
            #print(self.prior_token)
            #print(self.token)
            #print('')
            if not self.inNml:
              if self.token in ('&', '$'): # we saw a start indicator
                self.inNml = True
              elif self.token in ('end', None):
                pass
              if self.prior_token not in ('end', None, '&', '$'):
                self.endThis = True
            else: # inNml
              if self.token in ('&','$'):
                self.inNml = False
                self.thisLine = self.tokens.lineno

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
      headerNml = parser.read(self.wfp)
      #headerNml = f90nml.read(self.wfp)
      
      self.nHeaderLines = parser.thisLine + 1
      
      for commandSet in headerNml.items(): # loop through the command types
        command = commandSet[0]
        instances = commandSet[1]
        if command == 'description':
            for (attribute, value) in instances.items():
                self.description[attribute] = value
        elif command == 'column': # TODO: test this when there's only 1 column defined
          self.tableCols = []
          for commands in instances:
            tableCol = {}
            for (attribute,value) in commands.items():
              tableCol[attribute] = value
            self.tableCols.append(tableCol)
        elif command == 'parameter':
          self.parameters = []
          for commands in instances:
            parameter = {} 
            for (attribute, value) in commands.items():
              parameter[attribute] = value
            if 'fixed_value' in parameter:
              parameter['value'] = parameter['fixed_value']
            else:
              self.nParameters = self.nParameters +1
            self.parameters.append(parameter)
        elif command == 'array':
          self.arrays = []
          for commands in instances:
            array = {}
            for (attribute, value) in commands.items():
              array[attribute] = value
            if 'dimensions' not in array:
              array['dimensions'] = 1 # set default array dims
            self.arrays.append(array)
        elif command == 'include':
          eprint('Error: include command not yet supported!')
          return
        elif command == 'data':
          for (attribute,value) in instances.items():
            self.data[attribute] = value
        else:
          eprint('Unrecognized command in header: ' + command)
      
      if self.arrays != None:
        self.nArrays = len(self.arrays)
      
      self.wfp.seek(0)
      self.header = ''
      for i in range(self.nHeaderLines):
        self.header = self.header + self.wfp.readline()
      
      # take care of additional header lines
      nExtraHeader = self.data['additional_header_lines']
      while nExtraHeader > 0:
        self.header = self.header + self.getLine()
        nExtraHeader = nExtraHeader - 1
      
      #self.switchToBinMode()      
      
      self.nPages = 0
      # read the data page lines
      while (True): # a failed line read on end of file will kick us out
        dataPage = {}
        # first the parameters
        if self.parameters is not None:
          dataPage['parameters'] = {}
          for param in self.parameters:
            pCopy = dict(param)
            del pCopy['name']
            dataPage['parameters'][param['name']] = pCopy
            if 'value' not in dataPage['parameters'][param['name']]:
              try:
                data = self.getLine()
              except:
                return
              if dataPage['parameters'][param['name']]['type'] in ('short', 'long'):
                dataPage['parameters'][param['name']]['value'] = int(data)
              elif dataPage['parameters'][param['name']]['type'] in ('float', 'double'):
                dataPage['parameters'][param['name']]['value'] = float(data)
              else:
                if hasattr(data,'decode'):
                  dataPage['parameters'][param['name']]['value'] = data.decode('utf-8')
                else:
                  dataPage['parameters'][param['name']]['value'] = data
        
        # next we read the arrays
        if self.arrays is not None:
          dataPage['arrays'] = {}
          for array in self.arrays:
            aCopy = dict(array)
            del aCopy['name']
            dataPage['arrays'][array['name']] = aCopy
            try:
              dataLine = self.getLine()
            except:
              return
            # figure out how many elements in each dimension
            if dataPage['arrays'][array['name']]['dimensions'] > 1:
              splitData = dataLine.split()
              nElements = []
              for element in splitData:
                nElements.append(int(element))
            else: # only one dim
              nElements = int(dataLine)
            
            # compute total number of elements
            if hasattr(nElements, '__iter__'):
              totElements = np.prod(nElements)
            else:
              totElements = nElements
            
            # now we'll read in the array
            if dataPage['arrays'][array['name']]['type'] == 'string':
              elementsRead = 0
              arrayVals = np.array([],dtype=str)
              while elementsRead < totElements:
                l = self.getLine()
                iol = io.StringIO(l)
                df = pd.read_csv(iol, delim_whitespace=True,header=None)
                arrayLine = df.as_matrix()[0].astype(str)
                arrayVals = np.concatenate((arrayVals,arrayLine))
                elementsRead = elementsRead + len(arrayLine)
                
            elif dataPage['arrays'][array['name']]['type'] == 'character':
              eprint('Unsupported character array type')
              return
            else:
              remainingElements = totElements
              arrayType = dataPage['arrays'][array['name']]['type']
              if arrayType == 'short':
                converter = np.int16
              elif arrayType == 'long':
                converter = np.int32
              elif arrayType == 'float':
                converter = np.float32
              elif arrayType == 'double':
                converter = np.float64
              elif arrayType == 'boolean':
                converter = np.bool
              else:
                eprint('Unsupported array datatype')
                return
              
              arrayVals = np.fromfile(self.wfp,dtype=converter,count=totElements,sep=" ")
              #arrayVals = np.array([],dtype=converter)
              
              #elementsRead = 0
              #while elementsRead < totElements:
              #  data = self.getLine().split()
              #  arrayVals = arrayVals.append(np.array(data,dtype=converter))
              #  elementsRead = elementsRead + len(data)
                
              # reshape it to be what we expect
            arrayVals = arrayVals.reshape(nElements)
            dataPage['arrays'][array['name']]['value'] = arrayVals
              
        
                
        # and finally the table
        if self.tableCols is not None:
          try:
            if self.data['no_row_counts'] == 0:
              tableRows = int(self.getLine())
              tableData = ""
              for i in range(tableRows):
                tableData = tableData + self.getLine()
            else:
              tableLine = self.GetLine()
              tableData = ""
              while tableLine != "":
                tableData = tableData + tableLine
                tableLine = self.GetLine()
          except:
            return
          dataPage['table'] = tableData
        
        self.pageData.append(dataPage)
        self.nPages = self.nPages+1        