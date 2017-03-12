
#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
  name='sdds',
  version='0.12',
  description='pure python parser for SDDS (self describing data set) files',
  author='Grey Christoforo',
  author_email='grey@christoforo.net',
  url='https://github.com/greyltc/python-sdds',
  packages=find_packages(),
  classifiers=[
    # How mature is this project? Common values are
    #   3 - Alpha
    #   4 - Beta
    #   5 - Production/Stable
    'Development Status :: 3 - Alpha',
  ],
)
