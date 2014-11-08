#! /usr/bin/env python
"""
generate_obsIDs2mwacRTS_multi.py
Takes a list of obsIDs and generates a qsub script for downloading the data from NGAS (if requested), running ngas2mwaRTS.py and another qsub script for running the RTS  

09/08/13 - Added different functions for generating scripts on gstar and fornax given their quite different I/O structure
"""

##########

def generate_gstar(infile,basename,n_subbands,rts_templates,download,array,options):

    mwa_dir = os.getenv('MWA_DIR','/scratch/astronomy556/MWA/')
    cwd = os.getcwd()

    n_obs = sum(1 for line in open(infile))

    out_file = open('NGAS2mwacRTS_multi.sh','w+')
    
    out_file.write('#!/bin/bash\n')
    for line in in_file:
        obs_id = (line.split())[0]
        if(download):
            out_file.write('cd ' + mwa_dir + 'data\n')
            out_file.write('change_db.py curtin\n')
            out_file.write('obsresolve.py -r ngas01.ivec.org -s ngas01.ivec.org -o %s\n' % obs_id)
        data_dir = mwa_dir + 'data/%s' % obs_id    
        out_file.write('cd '+ data_dir +'\n')
        out_file.write('change_db.py curtin\n') 

        if(array == '32T'):
            out_file.write('ngas2uvfitssubbandsRTS.py %s %s %s %s %s\n' % (basename, data_dir, obs_id, n_subbands, rts_templates))
        else:
            out_file.write('ngas2mwacRTS.py %s %s %s %s %s\n' % (basename, data_dir, obs_id, n_subbands, rts_templates))

    # Command to write RTS qsub script

    out_file.write('cd %s\n' %cwd)
    out_file.write('generate_mwac_qRTS.py %s %s %s %s \n' % (infile, basename, n_subbands, rts_templates))

    out_file.close()
    


def generate_fornax(infile,basename,n_subbands,rts_templates,download,array,options):

    mwa_dir = os.getenv('MWA_DIR','/scratch/astronomy556/MWA/')
    cwd = os.getcwd()

    n_obs = sum(1 for line in open(infile))

    if options.do_erase is False:
        do_erase = ''
    else:
        do_erase = '--erase_GPUfiles'
    

    out_file = open('qNGAS2mwacRTS_multi.sh','w+')

    out_file.write('#!/bin/bash\n')
    out_file.write('#PBS -l select=1:ncpus=1:mem=8gb\n')
    out_file.write('#PBS -l walltime=00:%d:00\n' % (n_obs * 30))
    out_file.write('#PBS -m e\n')
    out_file.write('#PBS -q copyq\n')
    out_file.write('#PBS -W group_list=partner678\n')
    out_file.write('source ' + mwa_dir + 'bin/activate \n')


    for line in in_file:
        obs_id = (line.split())[0]
        if(download):
            out_file.write('cd ' + mwa_dir + 'data\n')
            #out_file.write('change_db.py curtin\n')
            out_file.write('obsresolve.py -r ngas01.ivec.org -s ngas01.ivec.org -o %s\n' % obs_id)
        data_dir = mwa_dir + 'data/%s' % obs_id    
        out_file.write('cd '+ data_dir +'\n')
#        out_file.write('change_db.py curtin\n')
        
        if(array == '32T'):
            out_file.write('ngas2uvfitssubbandsRTS.py %s %s %s %s %s\n' % (basename, data_dir, obs_id, n_subbands, rts_templates))
        else:
            out_file.write('ngas2mwacRTS.py %s %s %s %s %s\n' % (basename, data_dir, obs_id, n_subbands, rts_templates))

    # Command to write RTS qsub script

    out_file.write('cd $PBS_O_WORKDIR\n')
    if(options.auto_gen):
        out_file.write('generate_mwac_qRTS_auto.py %s %s %s %s --auto %s\n' % (infile, basename, n_subbands, rts_templates, do_erase))
    else:
        if options.use_metafits:
            out_file.write('generate_mwac_qRTS.py %s %s %s %s \n' % (infile, basename, n_subbands, rts_templates))
        else:
            out_file.write('generate_mwac_qRTS.py %s %s %s %s \n' % (infile, basename, n_subbands, rts_templates))

    out_file.write('deactivate\n')

    out_file.close()

##########

import sys,os, glob
from socket import gethostname
from optparse import OptionParser,OptionGroup

usage = 'Usage: generate_obsIDs2mwacRTS_multi.py [text file of obsIDs] [basename] [# of subbands] [rts_templates] [download 1=yes, 0=no] [array]'

parser = OptionParser(usage=usage)

parser.add_option('--auto',action="store_true",dest="auto_gen", help="Generate script to be run automatically from within qRTS_multi_wrapper")
parser.add_option('--erase_GPUfiles',action='store_true',dest='do_erase',default=False,help='Erase raw GPU files after processing [default=%default]')
parser.add_option('--use_metafits',action='store_true',dest='use_metafits',default=True,help='Use metafits file to gather metadata [default=%default]')

(options, args) = parser.parse_args()

infile = args[0]
basename = args[1]
n_subbands = args[2]
rts_templates = args[3]
download = int(args[4])
array = args[5]


hostname = gethostname()

try:
    in_file = open(infile)

except IOError, err:
    'Cannot open input file %s\n',str(infile)

if not (array == '32T' or array == '128T'):
    print 'Array Parameter should be \'32T\' or \'128T\''
    exit(1)


if(hostname == 'g2.hpc.swin.edu.au'):
    generate_gstar(infile,basename,n_subbands,rts_templates,download,array,options)
if(hostname == 'login1'):
    generate_fornax(infile,basename,n_subbands,rts_templates,download,array,options)




    
    
    



    
        
        
