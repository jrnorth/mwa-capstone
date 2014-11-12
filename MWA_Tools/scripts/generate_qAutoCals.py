#! /usr/bin/env python
""" 
generate_qAutoCals.py
Generates a qsub script to automatically download and process a set of EOR calibrators.
"""

import sys,os, glob
from optparse import OptionParser,OptionGroup

usage = 'Usage: generate_qAutoCals.py [options]\n'
usage += '\tGenerates a qsub script to automatically download\n'
usage += '\tand process a set of EOR calibrators.\n'

parser = OptionParser(usage=usage)
parser.add_option('-d','--datestring',dest='datestring',default=None,
                      help='Date of EOR Observations (yyyy-mm-dd)',type='string')
parser.add_option('--template', dest='templatefile',
                      help='List of RTS templates',type='string')
parser.add_option('--basename', dest='basename',default='autoCals',
                      help='Base name for generated files [default=%default]')
parser.add_option('--download',dest='download',default=True,
                      action='store_false',
                      help='Download GPU files from NGAS [default=%default]')
parser.add_option('--starttime',dest='starttime',default=None,
                      help='Time to start qsub job. The default is to start immediately')
parser.add_option('--erase_GPUfiles',action='store_true',dest='do_erase',default=False,help='Erase raw GPU files after processing [default=%default]')
    
(options, args) = parser.parse_args()
                      
    
# Write list of obsids. 
 
if options.datestring is None:
    print 'No date entered. Exiting...'
    sys.exit(1)
else:
    cmd = 'find_EOR_cals.py %s > CalsList_%s.dat' % (options.datestring,options.datestring)
    print 'Writing list of obsids to file: CalsList_%s.dat' % options.datestring
    os.system(cmd)

if options.download is True:
    download = 1
else:
    download = 0

if options.starttime is None:
    starttime = ''
else:
    starttime = '-a %s' % options.starttime

if options.do_erase is False:
    do_erase = ''
else:
    do_erase = '--erase_GPUfiles'

# Write qsub script

cwd = os.getcwd()

autofile = 'qAutoCals_%s.sh' % options.datestring

auto_file = open(autofile,'w+')

auto_file.write('#!/bin/bash\n')
auto_file.write('generate_obsIDs2mwacRTS_multi.py %s/CalsList_%s.dat %s 24 %s %d 128T --auto %s\n' % (cwd, options.datestring, options.basename, options.templatefile, download, do_erase))
auto_file.write('generate_mwac_qRTS_auto.py %s/CalsList_%s.dat %s 24 %s --auto %s\n' % (cwd, options.datestring, options.basename, options.templatefile,do_erase))
auto_file.write('chmod +x qRTS_auto_inner.sh\n')
auto_file.write('NGAS_JOB=$(qsub %s qNGAS2mwacRTS_multi.sh)\n' % starttime)
auto_file.write('echo $NGAS_JOB\n')
auto_file.write('RTS_JOB=$(qsub -W depend=afterok:$NGAS_JOB qRTS_auto_wrapper.sh)\n')
auto_file.write('echo $RTS_JOB\n')

## PP script here

auto_file.close()
print 'Wrote script file: qAutoCals_%s.sh' % options.datestring  

cmd = 'chmod +x qAutoCals_%s.sh' % options.datestring
os.system(cmd)
 


  




