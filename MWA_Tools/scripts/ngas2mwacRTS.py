#! /usr/bin/env python
"""

A python wrapper which does some setup to run the RTS directly on correlator GPU files. 

"""

import sys, os
from optparse import OptionParser,OptionGroup

usage = 'Usage: python ngas2mwacRTS [basename] [data_dir] [gps] [# of subbands] [rts_templates]' 

parser = OptionParser(usage=usage)

parser.add_option('--use_metafits',action='store_true',dest='use_metafits',default=True,help='Use metafits file to gather metadata [default=%default]')

(options, args) = parser.parse_args()

basename = args[0]
data_dir = args[1]
gpstime = args[2]
n_subbands = args[3]
rts_templates = args[4]

cmd = "make_metafits.py --gps=%s" % (gpstime)
print cmd
os.system(cmd)    

cmd = "make_metafiles.py -l --rts --gps=%s --header=header.txt --antenna=antenna_locations.txt --instr=instr_config.txt" % (gpstime)
print cmd
os.system(cmd)        



