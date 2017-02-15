#!/usr/bin/env python
import os
from pprint import pprint
from sdds import SDDS as ssds

ds = ssds('exampleData'+os.path.sep+'cityWeather.sdds')
pprint (vars(ds), width=1)

dsgz = ssds('exampleData'+os.path.sep+'cityWeather.sdds.gz')
pprint (vars(dsgz), width=1)