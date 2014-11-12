#! /usr/bin/env python
"""
generate_mwac_qRTS.py
Generates a qsub scripts to process a series of list of obsIDs. This script is run automatically at the end of qNGAS2mwacRTS_multi.sh

09/08/13 - Added different functions for generating scripts on gstar and fornax given their different network I/O systems.
"""

import sys,os, glob

###

def generate_gstar(infile,basename,n_subbands,rts_templates,array,options):

    try:
        in_file = open(infile)

    except IOError, err:
        'Cannot open input file %s\n',str(infile)

    mwa_dir = os.getenv('MWA_DIR','/scratch/partner678/MWA/')
    n_obs = sum(1 for line in open(infile))
    
    rts_file = open('qRTS_multi.sh','w+')

    rts_file.write('#!/bin/bash\n')

    # Set number of required nodes. Consider:
    # i) 2 GPUs per gstar node 
    # ii) potential missing GPU files
    # iii) set number of nodes for obsid with max number of GPU files 
    #      (may be different for different obsids) 

    max_bands = 0

    for line in in_file:
        obs_id = (line.split())[0]
        data_dir = mwa_dir + 'data/%s' % obs_id    

    # Account for missing correlator GPU files
        t00_files = glob.glob(data_dir + '/*gpubox*00.fits') 
        if(len(t00_files) < 1):
            t00_files = glob.glob(data_dir + '/*uvfits') 
        n_presentBands = len(t00_files)
        if(n_presentBands > max_bands):
            max_bands = n_presentBands
    
    n_nodes = (max_bands + 1) / 2
    if(n_nodes % 2):
        n_nodes += 1

    rts_file.write('#PBS -l nodes=%d:gpus=2\n' % int(n_nodes))
    rts_file.write('#PBS -l walltime=00:%d:00\n' % (n_obs * 15))
    rts_file.write('#PBS -m e\n')
    rts_file.write('#PBS -q sstar\n')
    rts_file.write('#PBS -A p048_astro\n')
    rts_file.write('source ' + mwa_dir + 'bin/activate \n')
    
    in_file.seek(0)

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

#        rts_file.write('auto_flag_rts.py %s\n' % obs_id)

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


def generate_fornax(infile,basename,n_subbands,rts_templates,array,options):

    try:
        in_file = open(infile)

    except IOError, err:
        'Cannot open input file %s\n',str(infile)

    mwa_dir = os.getenv('MWA_DIR','/scratch/partner678/MWA/')
    n_obs = sum(1 for line in open(infile))

    rts_file = open('qRTS_multi.sh','w+')

    rts_file.write('#!/bin/bash\n')
    rts_file.write('#PBS -l select=%d:ncpus=12:ngpus=1:mem=48gb:mpiprocs=1\n' % (int(n_subbands)))
    rts_file.write('#PBS -l walltime=00:%d:00\n' % (n_obs * options.timePerObs))
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
        rts_file.write('generate_RTS_in_mwac.py %s %s %s %s --templates=%s --header=%s.metafits\n' % (data_dir, basename, n_subbands,array,rts_templates,obs_id))

#        rts_file.write('auto_flag_rts.py %s\n' % obs_id)

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





###
from optparse import OptionParser,OptionGroup

usage = 'Usage: generate_mwac_qRTS.py [text file of obsIDs] [basename] [# of subbands] [rts_templates]'

parser = OptionParser(usage=usage)

parser.add_option('-t','--timePerObs',dest='timePerObs',default=15,type=int,help='walltime in minutes per obsid')

(options, args) = parser.parse_args()


infile = args[0]
basename = args[1]
n_subbands = args[2]
rts_templates = args[3]
array = '128T' # No 32T option for this script


try:
    in_file = open(infile)

except IOError, err:
    'Cannot open input file %s\n',str(infile)

mwa_dir = os.getenv('MWA_DIR','/scratch/partner678/MWA/')

if(mwa_dir == '/scratch/partner678/MWA/'):
    generate_fornax(infile,basename,n_subbands,rts_templates,array,options)
if(mwa_dir == '/lustre/projects/p048_astro/MWA/'):
    generate_gstar(infile,basename,n_subbands,rts_templates,array,options)

############
