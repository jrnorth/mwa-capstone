#! /usr/bin/env python
""" 
integrate_RTS_freq_over_time.py
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

import sys,os,glob
if (len(sys.argv) != 3):
    print 'Usage: integrate_RTS_freq_over_time.py [text file of obsIDs] [basename]'
else:
    infile = str(sys.argv[1])
    basename = str(sys.argv[2])

    try:
        in_file = open(infile)
    except IOError, err:
        'Cannot open input file %s\n',str(infile)

    mwa_dir = os.getenv('MWA_DIR','/scratch/partner678/MWA/')

    ArrayID = 1

    if(mwa_dir == '/scratch/partner678/MWA/'):
        ArrayID = os.getenv('PBS_ARRAY_INDEX',1)
    if(mwa_dir == '/lustre/projects/p048_astro/MWA/'):
        ArrayID = os.getenv('PBS_ARRAYID',1)

    nChannels = 24

    pwd = os.getenv('PBS_O_WORKDIR')
    os.chdir(pwd)
    
    channel_dir = 'ch_%s' % (int(ArrayID)-1)

    if not (os.access(channel_dir,os.R_OK)):
        os.mkdir(channel_dir)
    os.chdir(channel_dir)

    
    cmd = 'integrate_image -w -o all_%s_ch%s_integrated' % (basename,int(ArrayID)-1)

    for n in range(nChannels):
        if(n == int(ArrayID)-1):
            for line in in_file:
                obs_id = (line.split())[0]
                data_dir = mwa_dir + 'data/' + obs_id
                cmd += ' %s/%s_%s_ch%s_integrated.fits' % (data_dir,obs_id,basename,int(ArrayID)-1)
            print cmd
            os.system(cmd)

            cmd = 'convert_image -o all_ch%s_convert all_%s_ch%02d_integrated.fits -p SIN -r 0 -d -27.0 -x 1000 -y 1000 -P 4' % (n,basename,int(ArrayID)-1)
            print cmd
            os.system(cmd)
            cmd = 'mv projected.fits all_%s_ch%02d.fits' % (basename,int(ArrayID)-1)
            os.system(cmd)


