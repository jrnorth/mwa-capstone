#! /usr/bin/env python
import logging, sys, os, glob, subprocess, string, re, urllib, math, time
from optparse import OptionParser,OptionGroup
import numpy
import os

import ephem
from mwapy import convert_ngas, get_observation_info
from mwapy.obssched.base import schedule

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('convert_ngas')
logger.setLevel(logging.WARNING)

_GPUBOXNAME='gpubox'

def main():

    basename = str(sys.argv[1])

    gpstime=None

    n_inputs = 256
    n_channelsperfile = 32

    command=' '.join(sys.argv)
    parser = OptionParser()
    (options, args) = parser.parse_args()

#    parser = OptionParser(usage=usage)

# How many GPU boxes are there?
    
    t00_files = [filename for filename in args if 'gpubox' in filename and '00.fits' in filename]

    _NGPUBOX = len(t00_files)

    print 'NGPUBOX = ',_NGPUBOX 

    for file_00 in t00_files:
        name_parts=convert_ngas.parseNGASfile(file_00)
        box_number = int((name_parts[2])[len('gpubox'):])
        cmd = 'build_lfiles -m 1 -v %s -f %d -o %s_band%02d -i %d' % (file_00,n_channelsperfile,basename,box_number,n_inputs) 
        os.system(cmd)
        print cmd
        further_timesteps = [filename for filename in args if name_parts[2] in filename and filename.find('00.fits') == -1]

        # sort further timesteps ?
        for timestep in further_timesteps:
            cmd = 'build_lfiles -m 1 -v %s -f %d -o %s_band%02d -i %d -a' % (timestep,n_channelsperfile,basename,box_number,n_inputs) 
            os.system(cmd)
            print cmd

######################################################################
if __name__=="__main__":
    main()
        
        


#    cmd = "convert_ngas.py -v -t 4 -f 4 --gps=%s --lfile=%s -l -s %d --instr=instr_config.txt --header=header.txt %s/%s*.fits" % (gpstime,basename, n_subbands, data_dir,gpstime)    

    
