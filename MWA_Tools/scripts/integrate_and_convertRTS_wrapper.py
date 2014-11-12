#! /usr/bin/env python
""" 
integrate_and_convertRTS_wrapper.py
Wrapper for RTS post-processing utilities integrate_image and convert_image
Designed to be run within a PBS array job
"""

def parse_image_centre():

    try:
        in_file = open('header.txt')
    except IOError, err:
        'Cannot open header file %s\n',str(infile)

    ra_hrs = dec_degs = None

    for line in in_file:
        if(line.find('DEC_DEGS')==0):
            dec_degs = float((line.split())[1])
        if(line.find('RA_HRS')==0):
            ra_hrs = float((line.split())[1])

    if(ra_hrs != None and dec_degs != None):
        return ra_hrs, dec_degs
    else:
        print 'Error Reading Co-ordinates from header file'
        exit(1)

##########################################################

import sys,os
from socket import gethostname

if (len(sys.argv) != 3):
    print 'Usage: integrate_and_convertRTS_wrapper.py [text file of obsIDs] [basename]'
else:
    infile = str(sys.argv[1])
    basename = str(sys.argv[2])

    try:
        in_file = open(infile)
    except IOError, err:
        'Cannot open input file %s\n',str(infile)

    mwa_dir = os.getenv('MWA_DIR','/scratch/astronomy556/MWA/')

    ArrayID = 1

#    hostname = gethostname()  
#    if(hostname == 'login1'): # Fornax
#        ArrayID = os.getenv('PBS_ARRAY_INDEX',1)
#    if(hostname == 'g2.hpc.swin.edu.au'):
#        ArrayID = os.getenv('PBS_ARRAYID',1)

    if(mwa_dir == '/scratch/astronomy556/MWA/'):
        ArrayID = os.getenv('PBS_ARRAY_INDEX',1)
    if(mwa_dir == '/lustre/projects/p048_astro/MWA/'):
        ArrayID = os.getenv('PBS_ARRAYID',1)


    line_count = 1
    for line in in_file:
        obs_id = (line.split())[0]
        if(line_count == int(ArrayID)):
            data_dir = mwa_dir + 'data/' + obs_id
            print data_dir
            os.chdir(data_dir)
            integrate_cmd = 'integrate_image -w -o %s_%s_integrated *MHz_%s_*.fits' % (basename, obs_id,basename)
            print integrate_cmd
            os.system(integrate_cmd)
            ra_hrs, dec_degs = parse_image_centre()
            convert_cmd = 'convert_image -o %s_%s_converted %s_%s_integrated.fits -p SIN -r %s -d %s -x 2000 -y 2000 -P 4' % (basename, obs_id, basename, obs_id, ra_hrs * 15.0, dec_degs)
            print convert_cmd
            os.system(convert_cmd)
            project_cmd = 'mv projected.fits %s_%s_projected.fits' % (basename, obs_id)
            print project_cmd
            os.system(project_cmd)
        line_count += 1    

    in_file.close()

