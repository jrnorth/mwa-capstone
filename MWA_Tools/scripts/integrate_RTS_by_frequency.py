#! /usr/bin/env python
""" 
integrate_RTS_by_frequency.py
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
    print 'Usage: integrate_RTS_by_frequency.py [text file of obsIDs] [basename]'
else:
    infile = str(sys.argv[1])
    basename = str(sys.argv[2])

    try:
        in_file = open(infile)
    except IOError, err:
        'Cannot open input file %s\n',str(infile)

    mwa_dir = os.getenv('MWA_DIR','/scratch/astronomy556/MWA/')

    ArrayID = 1

    if(mwa_dir == '/scratch/astronomy556/MWA/'):
        ArrayID = os.getenv('PBS_ARRAY_INDEX',1)
    if(mwa_dir == '/lustre/projects/p048_astro/MWA/'):
        ArrayID = os.getenv('PBS_ARRAYID',1)

    nChannels = 24

    line_count = 1
    for line in in_file:
        obs_id = (line.split())[0]
        if(line_count == int(ArrayID)):
            data_dir = mwa_dir + 'data/' + obs_id
            print data_dir
            os.chdir(data_dir)
            file_list = glob.glob('2*int*MHz*chan*')
            file_list.sort()
            filesPerNode = len(file_list) / nChannels
            for n in range(nChannels):

                cmd = 'integrate_image -w -o %s_%s_ch%02d_integrated' % (obs_id,basename, n)
                for i in range(filesPerNode):
                    cmd += ' %s' % file_list[n*filesPerNode + i]
                    
                print cmd
                os.system(cmd)

        line_count += 1

    in_file.close()

