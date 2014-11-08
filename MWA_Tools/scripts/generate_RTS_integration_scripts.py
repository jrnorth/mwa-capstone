#! /usr/bin/env python
""" 
generates qsub scripts for integrating the Healpix outputs from a list of obsids. Writes qRTS_integrate.py which integrates each obsid across time and frequency
and qRTS_freq_integrate.py which integrates each coarse channel across obs and time
"""

def generate_gstar(infile,basename):
    
    n_obs = sum(1 for line in open(infile))

    integrate_file = open('qRTS_integrate.sh','w+')
    integrate_file.write("#!/bin/bash \n")
    integrate_file.write("#PBS -l nodes=1\n")
    integrate_file.write("#PBS -t 1-%s \n" %  n_obs)
    integrate_file.write("#PBS -l walltime=00:15:00 \n")
    integrate_file.write("#PBS -m e\n")
    integrate_file.write("#PBS -q sstar\n")
    integrate_file.write("#PBS -W p048_astro\n")
    
    integrate_file.write("source /lustre/projects/p048_astro/MWA/bin/activate\n")
    integrate_file.write("integrate_and_convertRTS_wrapper.py %s %s \n" % (infile,basename))
    integrate_file.write("deactivate\n")

    integrate_file.close()

    integrate_file = open('qRTS_frequency_integrate.sh','w+')
    integrate_file.write("#!/bin/bash \n")
    integrate_file.write("#PBS -l nodes=1\n")
    integrate_file.write("#PBS -t 1-%s \n" %  n_obs)
    integrate_file.write("#PBS -l walltime=00:%s:00 \n" % (2 * n_obs) )
    integrate_file.write("#PBS -m e\n")
    integrate_file.write("#PBS -q sstar\n")
    integrate_file.write("#PBS -W p048_astro\n")
    
    integrate_file.write("source /lustre/projects/p048_astro/MWA/bin/activate\n")
    integrate_file.write("integrate_RTS_by_frequency.py %s %s \n" % (infile,basename))
    integrate_file.write("deactivate\n")

    integrate_file.close()

    n_channels = 24

    integrate_file = open('qRTS_time_integrate.sh','w+')
    integrate_file.write("#!/bin/bash \n")
    integrate_file.write("#PBS -l nodes=1\n")
    integrate_file.write("#PBS -t 1-%s \n" %  n_channels)
    integrate_file.write("#PBS -l walltime=00:15:00 \n")
    integrate_file.write("#PBS -m e\n")
    integrate_file.write("#PBS -q sstar\n")
    integrate_file.write("#PBS -W p048_astro\n")
    
    integrate_file.write("source /lustre/projects/p048_astro/MWA/bin/activate\n")
    integrate_file.write("integrate_RTS_freq_over_time.py %s %s \n" % (infile,basename))
    integrate_file.write("deactivate\n")

    integrate_file.close()




def generate_fornax(infile,basename):

    n_obs = sum(1 for line in open(infile))
    
    integrate_file = open('qRTS_integrate.sh','w+')
    integrate_file.write("#!/bin/bash \n")
    integrate_file.write("#PBS -l select=1:mem=12gb \n")
    if(n_obs > 1):
        integrate_file.write("#PBS -J 1-%s \n" %  n_obs)
    integrate_file.write("#PBS -l walltime=00:15:00 \n")
    integrate_file.write("#PBS -m e \n")
    integrate_file.write("#PBS -q workq \n")
    integrate_file.write("#PBS -W group_list=astronomy556 \n")

    integrate_file.write("source /scratch/astronomy556/MWA/bin/activate \n")
    integrate_file.write("integrate_and_convertRTS_wrapper.py %s %s \n" % (infile,basename))
    integrate_file.write("deactivate\n")

    integrate_file.close()

    integrate_file.close()

###

import sys,os

if (len(sys.argv) != 3):
    print 'Usage: generate_RTS_integration_scripts.py [text file of obsIDs] [basename]'
else:
    infile = str(sys.argv[1])
    basename = str(sys.argv[2])

    try:
        in_file = open(infile)
    except IOError, err:
        'Cannot open input file %s\n',str(infile)

    mwa_dir = os.getenv('MWA_DIR','/scratch/astronomy556/MWA/')

    if(mwa_dir == '/scratch/astronomy556/MWA/'):
        generate_fornax(infile,basename)
    if(mwa_dir == '/lustre/projects/p048_astro/MWA/'):
        generate_gstar(infile,basename)

    
        
