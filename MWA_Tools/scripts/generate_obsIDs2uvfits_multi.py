#! /usr/bin/env python
"""
generate_qNAGS2uvfitssubbands_multi.py
Takes a list of obsIDs and generates a qsub script for running ngas2uvfitssubbands on the data, previously obtained using obsresolve_list.py
"""

import sys,os, glob

if (len(sys.argv) != 7):
    print 'Usage: generate_obsIDs2uvfits.py [text file of obsIDs] [basename] [# of subbands] [rts_templates] [download 1=yes, 0=no] [array]'
else:
    infile = str(sys.argv[1])
    basename = str(sys.argv[2])
    n_subbands = str(sys.argv[3])
    rts_templates = str(sys.argv[4])
    download = int(sys.argv[5])
    array = str(sys.argv[6])

    mwa_dir = os.getenv('MWA_DIR','/scratch/astronomy556/MWA/')

    try:
        in_file = open(infile)
    except IOError, err:
        'Cannot open input file %s\n',str(infile)

    if not (array == '32T' or array == '128T'):
        print 'Array Parameter should be \'32T\' or \'128T\''
        exit(1)
    

    n_obs = sum(1 for line in open(infile))

    out_file = open('qNGAS2uvfits_multi.sh','w+')

    out_file.write('#!/bin/bash\n')
    out_file.write('#PBS -l select=1:ncpus=1:mem=8gb\n')
    out_file.write('#PBS -l walltime=00:%d:00\n' % (n_obs * 60))
    out_file.write('#PBS -m e\n')
    out_file.write('#PBS -q copyq\n')
    out_file.write('#PBS -W group_list=astronomy556\n')
    out_file.write('source ' + mwa_dir + 'bin/activate \n')

    # Also generate qsub script to run generated RTS .in files

    rts_file = open('qRTS_multi.sh','w+')

    rts_file.write('#!/bin/bash\n')
    rts_file.write('#PBS -l select=%d:ncpus=12:ngpus=1:mem=16gb:mpiprocs=1\n' % (int(n_subbands)+1))
    rts_file.write('#PBS -l walltime=00:%d:00\n' % (n_obs * 15))
    rts_file.write('#PBS -m e\n')
    rts_file.write('#PBS -q workq\n')
    rts_file.write('#PBS -W group_list=astronomy556\n')
    rts_file.write('source ' + mwa_dir + 'bin/activate \n')
    
    for line in in_file:
        obs_id = (line.split())[0]
        if(download):
            out_file.write('cd ' + mwa_dir + 'data\n')
            out_file.write('change_db.py curtin\n')
            out_file.write('bp_obsresolve.py -r ngas01.ivec.org -s ngas01.ivec.org -o %s\n' % obs_id)
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
#
#
        rts_file.write('generate_RTS_in.py %s %s %s %s --templates=%s\n' % (data_dir, basename, n_subbands,array,rts_templates))

        rts_file.write('auto_flag_rts.py %s\n' % obs_id)

#
#
    # Account for missing correlator GPU files
        if(array=='128T'):
            t00_files = glob.glob(data_dir + '/*gpubox*00.fits') 
            if(len(t00_files) < 1):
                # in the case that the gpu files have been removed
                t00_files = glob.glob(data_dir + '/*uvfits') 
            n_presentBands = len(t00_files)

#            print 't_00', n_presentBands

        for line in template_list_file:
            if(array=='128T'):
                rts_file.write('mpirun -np %d rts_gpu %s_rts_%d.in\n' % (int(n_presentBands)+1, basename, rts_file_index))
            else:
                rts_file.write('mpirun -np %d rts_gpu %s_rts_%d.in\n' % (int(n_subbands)+1, basename, rts_file_index))
            rts_file_index += 1
        template_list_file.close()

    out_file.write('deactivate\n')

    out_file.close()
    rts_file.close()

    # Generate qsub script to integrate and convert MWA Healpix images

    int_file = open('qRTS_integrate.sh','w+')

    int_file.write('#!/bin/bash\n')
    
    int_file.write('#PBS -l select=1:ncpus=12:ngpus=1:mem=32gb\n')
    int_file.write('#PBS -l walltime=00:%d:00\n' % (n_obs * 15))
    if(n_obs > 1):
        int_file.write('#PBS -J 1-%d\n' % (n_obs))
    int_file.write('#PBS -m e\n')
    int_file.write('#PBS -q workq\n')
    int_file.write('#PBS -W group_list=astronomy556\n')
    int_file.write('source ' + mwa_dir + 'bin/activate \n')
    int_file.write('integrate_and_convertRTS_wrapper.py %s %s\n' % (infile, basename))
    int_file.write('deactivate \n')

    int_file.close()
    
    

    
    
    



    
        
        
