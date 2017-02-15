class SDDS:
  description = ["", ""]
  version = None
  def __init__(self, fileName=None):
    if fileName is not None:
      fp = open(fileName)
      f = fp.read()
      fp.close()
      lines = f.split('\n')
      #lines[0]
      for line in lines:
        print (line)