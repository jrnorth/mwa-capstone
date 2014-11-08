#! /usr/bin/env python
"""
generate_mwac_qRTS_auto.py
Generates a qsub scripts to process a series of list of obsIDs. This script is run automatically at the end of qNGAS2mwacRTS_multi.sh
04/09/13: Writes a two part 

"""

import sys,os, glob
from optparse import OptionParser,OptionGroup

usage = 'Usage: generate_mwac_qRTS.py [text file of obsIDs] [basename] [# of subbands] [rts_templates]'

parser = OptionParser(usage=usage)

parser.add_option('--auto',action="store_true",dest="auto_gen", help="Generate script to be run automatically from within qRTS_multi_wrapper")
parser.add_option('--no_upload',action='store_true',dest='no_upload',default=False,help='Do not upload cal solution to eorlive webpage [default=%default]')
parser.add_option('--erase_GPUfiles',action='store_true',dest='do_erase',default=False,help='Erase raw GPU files after processing [default=%default]')

(options, args) = parser.parse_args()

infile = args[0]
basename = args[1]
n_subbands = int(args[2])
rts_templates = args[3]
array = '128T' # No 32T option for this script


mwa_dir = os.getenv('MWA_DIR','/scratch/partner678/MWA/')

try:
    in_file = open(infile)

except IOError, err:
    'Cannot open input file %s\n',str(infile)

n_obs = sum(1 for line in open(infile))


if (options.auto_gen):

    rts_file = open('qRTS_auto_wrapper.sh','w+')
    rts_file.write('#!/bin/bash\n')
    rts_file.write('#PBS -l select=%d:ncpus=12:ngpus=1:mem=16gb:mpiprocs=1\n' % (int(n_subbands)+1))
    rts_file.write('#PBS -l walltime=00:%d:00\n' % (n_obs * 15))
    rts_file.write('#PBS -m e\n')
    rts_file.write('#PBS -q workq\n')
    rts_file.write('#PBS -W group_list=partner678\n')
    rts_file.write('source ' + mwa_dir + 'bin/activate \n')
    rts_file.write('cd $PBS_O_WORKDIR\n')
    rts_file.write('./qRTS_auto_inner.sh\n')
    if not options.no_upload:
        rts_file.write('cd /scratch/partner678/pprocopio/AutoCalPlot/\n')
        rts_file.write('./RTS_cal_up.py --list=%s\n' % infile)

    rts_file.close() 

    rts_file = open('qRTS_auto_inner.sh','w+')
    for line in in_file:
        obs_id = (line.split())[0]
        data_dir = mwa_dir + 'data/%s' % obs_id    
        rts_file.write('cd '+ data_dir +'\n')
        
        try:
            template_list_file = open(rts_templates)
        except IOError, err:
            'Cannot open list of RTS template files %s\n' % rts_templates
        rts_file_index = 0
        rts_file.write('generate_RTS_in_mwac.py %s %s %s %s --templates=%s\n' % (data_dir, basename, n_subbands,array,rts_templates))

        rts_file.write('auto_flag_rts.py %s\n' % obs_id)

    # Account for missing correlator GPU files
        t00_files = glob.glob(data_dir + '/*gpubox*00.fits') 
        if(len(t00_files) < 1):
            t00_files = glob.glob(data_dir + '/*uvfits') 
        n_presentBands = len(t00_files)

        for line in template_list_file:
            rts_file.write('mpirun -np %d rts_gpu %s_rts_%d.in\n' % (int(n_presentBands)+1, basename, rts_file_index))
            rts_file_index += 1
        template_list_file.close()
        
        # Clean up
        if options.do_erase:
            rts_file.write('rm *gpubox*.fits\n')

    rts_file.close()
    

else:

    rts_file = open('qRTS_multi.sh','w+')

    rts_file.write('#!/bin/bash\n')
    rts_file.write('#PBS -l select=%d:ncpus=12:ngpus=1:mem=16gb:mpiprocs=1\n' % (int(n_subbands)+1))
    rts_file.write('#PBS -l walltime=00:%d:00\n' % (n_obs * 15))
    rts_file.write('#PBS -m e\n')
    rts_file.write('#PBS -q workq\n')
    rts_file.write('#PBS -W group_list=partner678\n')
    rts_file.write('source ' + mwa_dir + 'bin/activate \n')

    for line in in_file:
        obs_id = (line.split())[0]
        data_dir = mwa_dir + 'data/%s' % obs_id    
        rts_file.write('cd '+ data_dir +'\n')
        
        try:
            template_list_file = open(rts_templates)
        except IOError, err:
            'Cannot open list of RTS template files %s\n' % rts_templates
        rts_file_index = 0
#
#
        rts_file.write('generate_RTS_in_mwac.py %s %s %s %s --templates=%s\n' % (data_dir, basename, n_subbands,array,rts_templates))

        rts_file.write('auto_flag_rts.py %s\n' % obs_id)

#
#
    # Account for missing correlator GPU files
        t00_files = glob.glob(data_dir + '/*gpubox*00.fits') 
        if(len(t00_files) < 1):
            t00_files = glob.glob(data_dir + '/*uvfits') 
        n_presentBands = len(t00_files)

#            print 't_00', n_presentBands

        for line in template_list_file:
            rts_file.write('mpirun -np %d rts_gpu %s_rts_%d.in\n' % (int(n_presentBands)+1, basename, rts_file_index))
            rts_file_index += 1
        template_list_file.close()

    rts_file.close()
