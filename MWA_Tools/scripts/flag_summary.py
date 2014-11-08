"""
read a list of ms and print the fraction of data flagged [%]
ex
casapy --nologger -c flag_summary.py *.ms
"""
from time import time
import numpy as n
import aipy as a
import sys,os,optparse
import re
t0 = time()

import mwapy
import mwapy.get_observation_info
from mwapy.obssched.base import schedule

db=schedule.getdb()

####################################
##     Parse inputs               ##
####################################
o = optparse.OptionParser()
o.set_usage('flag_summary.py [options] *.ms')
o.set_description(__doc__)
for i in range(len(sys.argv)):
    if sys.argv[i]==inspect.getfile( inspect.currentframe()):break
opts, args = o.parse_args(sys.argv[i+1:])

for vis in args:
    ms.open(vis)
    rec = ms.getdata(['flag'])
    print "%s %7.5%%"%(vis,n.mean(rec['flag'])*100)

