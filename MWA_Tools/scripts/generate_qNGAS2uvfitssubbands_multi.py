#! /usr/bin/env python
"""
generate_qNAGS2uvfitssubbands_multi.py
Takes a list of obsIDs and generates a qsub script for running ngas2uvfitssubbands on the data, previously obtained using obsresolve_list.py
"""

import sys, os

if (len(sys.argv) != 5):
    print 'Usage: generate_qNGAS2uvfitssubbands.py [text file of obsIDs] [basename] [# of subbands] [rts_templates] [array]'
else:
    infile = str(sys.argv[1])
    basename = str(sys.argv[2])
    n_subbands = str(sys.argv[3])
    rts_templates = str(sys.argv[4])
    array = str(sys.argv[5])
    
    mwa_dir = os.getenv('MWA_DIR','/scratch/astronomy556/MWA/')


    
    try:
        in_file = open(infile)
    except IOError, err:
        'Cannot open input file %s\n',str(infile)

    if not (array == '32T' or array == '128T'):
        print 'Array Parameter should be \'32T\' or \'128T\''
        exit(1)

    out_file = open('qNGAS2uvfits_multi.sh','w+')

    out_file.write('#!/bin/bash\n')
    out_file.write('#PBS -l nodes=1\n')
    out_file.write('#PBS -l walltime=00:60:00\n')
    out_file.write('#PBS -m e\n')
    out_file.write('#PBS -q copyq\n')
    out_file.write('#PBS -W group_list=astronomy556\n')
    out_file.write('source ' + mwa_dir + 'bin/activate \n')

    # Also generate qsub script to run generated RTS .in files
    
    rts_file = open('qRTS_multi.sh','w+')

    rts_file.write('#!/bin/bash\n')
    rts_file.write('#PBS -l select=%d:ncpus=1:ngpus=1:mem=8gb\n' % (int(n_subbands)+1))
    rts_file.write('#PBS -l walltime=00:60:00\n')
    rts_file.write('#PBS -m e\n')
    rts_file.write('#PBS -q workq\n')
        rts_file.write('#PBS -W group_list=astronomy556\n')
    
    for line in in_file:
        obs_id = (line.split())[0]
        if(download):
            out_file.write('cd ' + mwa_dir + 'data\n')
            out_file.write('obsresolve.py -r ngas01.ivec.org -s ngas01.ivec.org -o %s\n' % obs_id)
        data_dir = mwa_dir + 'data/%s' % obs_id 
        out_file.write('cd '+ data_dir +'\n')
        rts_file.write('cd '+ data_dir +'\n')
        out_file.write('change_db.py curtin\n')
        
        if(array == '32T'):
            out_file.write('ngas2uvfitssubbandsRTS.py %s %s %s %s %s\n' % (basename, data_dir, obs_id, n_subbands, rts_templates))
        else:
            out_file.write('ngas2uvfitssubbandsRTS_128T.py %s %s %s %s %s\n' % (basename, data_dir, obs_id, n_subbands, rts_templates))

        try:
            template_list_file = open(rts_templates)
        except IOError, err:
            'Cannot open list of RTS template files %s\n' % rts_templates
        rts_file_index = 0
        for line in template_list_file:
            rts_file.write('mpirun -np %d rts_gpu %s_rts_%d.in\n' % (int(n_subbands)+1, basename, rts_file_index))
            rts_file_index += 1
        template_list_file.close()

    out_file.write('deactivate\n')

    out_file.close()
    rts_file.close()



    
        
        
