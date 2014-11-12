"""
CASA wrapper for autoflag
execute with
casapy --nologger -c SIP/bash_SIP.py <OBSIDS>
assumes directory structure
cwd/<obsid>/<obsid>.uvfits
"""
import os,optparse
from pylab import *
####################################
##     Parse inputs               ##
####################################
o = optparse.OptionParser()
o.set_usage('bash_autoflag.py [options] *.ms')
o.set_description(__doc__)
for i in range(len(sys.argv)):
    if sys.argv[i]==inspect.getfile( inspect.currentframe()):break
opts, args = o.parse_args(sys.argv[i+1:])



#clean off the casa args:
for i in range(len(sys.argv)):
    if sys.argv[i]==inspect.getfile( inspect.currentframe()):break
obslist = sys.argv[i+1:]
print obslist
print "checking that they all exist"
myobslist = []
for obs in obslist:
    if os.path.exists(obs):myobslist.append(obs)
del(obslist)
if len(myobslist)<1: 
    print "no obs directories found here",os.getcwd()
    sys.exit(1)
print myobslist
print "starting the autoflagger"
for obsid in myobslist:
    uvfits = obsid + '/' + obsid + '.uvfits'
    vis = obsid + '/' + obsid + '.ms'
    if not os.path.exists(vis):
        print "importing uvfits"
        importuvfits(fitsfile=uvfits,vis=vis)
    execfile('/home/djacobs/src/MWA_Tools/scripts/auto_flag.py')
    savefig(obsid+'/'+obsid+'_flagspectrum.png')
