#! /usr/bin/env python
"""
run_Cotter_array.py
Runs cotter for the RTS on a single obsid, run inside a qsub array job
"""

import sys,os
from socket import gethostname

if (len(sys.argv) != 2):
    print 'Usage: run_Cotter_array.py [text file of obsIDs]'
else:
    infile = str(sys.argv[1])

    try:
        in_file = open(infile)
    except IOError, err:
        'Cannot open input file %s\n',str(infile)

    mwa_dir = os.getenv('MWA_DIR','/scratch/astronomy556/MWA/')

    ArrayID = os.getenv('PBS_ARRAY_INDEX')
    if(ArrayID == None):
        ArrayID = os.getenv('PBS_ARRAYID',1)
    

#    hostname = gethostname()  
#    if(hostname == 'login1'): # Fornax
#        ArrayID = os.getenv('PBS_ARRAY_INDEX',1)
#    if(hostname == 'g2.hpc.swin.edu.au'):
#        ArrayID = os.getenv('PBS_ARRAYID',1)

        
    line_count = 1
    for line in in_file:
        obs_id = (line.split())[0]
        if(line_count == int(ArrayID)):
            data_dir = mwa_dir + 'data/' + obs_id
            print data_dir
            os.chdir(data_dir)
            cotter_cmd = 'make_metafits.py --gps=%s' % obs_id
            print cotter_cmd
            os.system(cotter_cmd)
            # Note special formatting required due to control character '%' in string
            cotter_cmd = '/scratch/astronomy556/code/bin/cotter -m %s.metafits -o %s-%%%%.mwaf -mem 90 *gpubox*.fits' % (obs_id, obs_id)
            print cotter_cmd
            os.system(cotter_cmd)

        line_count += 1   

    in_file.close()

    
