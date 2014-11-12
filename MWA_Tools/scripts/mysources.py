#! /usr/bin/env python
"""
mysources.py 
D. Jacobs
July 2012

Note: Source selection default is 10 Jys at 150MHz

"""
from time import time
import numpy as n
import aipy as a
import sys,os,optparse


################################################################
##     Parse inputs
####################################
o = optparse.OptionParser()
o.set_usage('bash_delaycal.py [options] *.ms')
o.set_description(__doc__)
a.scripting.add_standard_options(o,cal=True,src=True)
o.add_option('--beamtype',default='MWA',
    help='Options include MWA [default] and Other')
o.add_option('--altaz',default='90,0',
    help='Altitude and Azimuth [degrees,degrees]. Default = 90,0')
o.add_option('-b','--beamformer_quantization',default=6.8,
    help='quantization of beamformer in degrees. default = 6.8')
o.add_option('-d','--obsdate',default=2455746.0,
    help="Observation date in GPS seconds or Julian date. Yeah, its that smart.")
o.add_option('-c','--src_lock',type='str',default=None,
    help='Choose pointing nearest this source (override altaz)')
opts, args = o.parse_args(sys.argv[1:])
###################################################

n.set_printoptions(suppress=True)


########################
# function definitions #
########################
def dB(x):
    return 10*n.log10(x)
def altaz2sweetspot(alt,az,db=6.808,tiledim=4):
    #input altitude and azimuth in degrees
    az  += 180 #azimuth is defined opposite the numpy matrix def.
    alt *= n.pi/180
    az *= n.pi/180
    db *= n.pi/180
    N = n.round(n.sin(n.pi/2 - alt) / n.sin(db) * n.cos(az))
    E = n.round(n.sin(n.pi/2 - alt) / n.sin(db) * n.sin(az))
    de = n.linspace(0,tiledim-1,num=4)*E
    dn = n.linspace(0,tiledim-1,num=4)*N
    dE,dN = n.meshgrid(de,dn)
    if N<0: dN = n.abs(n.flipud(dN))
    if E<0: dE = n.abs(dE)
    else: dE = n.fliplr(dE)
    return n.ravel(dN + dE).astype(int)

def nearestsweetspot_altaz(alt,az,db=6.808):
    alt *= n.pi/180
    az *= n.pi/180
    db *= n.pi/180
    N = n.round(n.sin(n.pi/2 - alt) / n.sin(db) * n.cos(az))
    E = n.round(n.sin(n.pi/2 - alt) / n.sin(db) * n.sin(az))
#    N,E = n.sin(n.pi/2-alt*n.pi/180) * n.cos(az*n.pi/180)/n.sin(db*n.pi/180),\
#        n.sin(n.pi/2-alt*n.pi/180) * n.sin(az*n.pi/180)/n.sin(db*n.pi/180)
    nearest_alt = 90-n.sqrt(n.arcsin(N*db)**2 + n.arcsin(E*db)**2)*180/n.pi
    nearest_az = n.arctan(E/float(N))*180/n.pi
    print nearest_az
    if az>n.pi/2.:nearest_az += 180
    if nearest_az<0: nearest_az += 360
    
    return nearest_alt,nearest_az


def pjys(src,aa,pol='XX'):
    src.compute(aa)
    if pol=='XX':
        bm = aa[0].bm_response(src.get_crds('top'))
    else:
        bm = aa[1].bm_response(src.get_crds('top'))
    return src.jys*bm
########################
# Parse the inputs     #
########################
try:
    str(opts.obsdate)
    T = None

except:
    if opts.obsdate/1027201150.>0.01: # we have a GPS time
        T = opts.obsdate/(3600*24.) + 2444244.5 #convert to Julian date
        GPS_Time = opts.obsdate
    else:
        T = opts.obsdate
        GPS_Time = (opts.obsdate - 2444244.5)*(3600*24.)

#get the beam parms
alt,az = map(float,opts.altaz.split(','))
    

if opts.src is None: opts.src='10/0.15'
aipycalfile = opts.cal
srclist,cutoff,catalogs = a.scripting.parse_srcs(opts.src, opts.cat)
######################
# Load the antenna array and beam model
##############

def get_aa(cal_key,freqs,bm_delays=None):
    exec('from %s import get_aa as _get_aa' % cal_key)
    return _get_aa(freqs,bm_delays)

if opts.beamtype=='MWA':
    bm_delays = altaz2sweetspot(alt,az,opts.beamformer_quantization)
    nearest_alt,nearest_az = nearestsweetspot_altaz(alt,az)
    aa = get_aa(aipycalfile,n.array([0.160]),bm_delays=bm_delays)
else:
    aa = a.cal.get_aa(aipycalfile,n.array([0.160]))
    bm_delays = None
    nearest_alt,nearest_az = alt,az
if T is None:
    aa.date = opts.obsdate
    GPS_Time = (aa.get_jultime() - 2444244.5)*(3600*24.)
    T = aa.get_jultime()
else:
    aa.set_jultime(T)

#lock on to our primary source (if given)
if not opts.src_lock is None:
    if opts.cal != None:
        lockcat = a.cal.get_catalog(opts.cal, [opts.src_lock], None, catalogs)
    else:
        lockcat = a.src.get_catalog(opts.src_lock, None, catalogs)
    locksrc = lockcat[opts.src_lock]
    locksrc.compute(aa)
    alt,az = locksrc.alt*180/n.pi,locksrc.az*180/n.pi

############################
# Load the catalog  ########
############################
#add on the Sun and the Moon 
if srclist is None:
    srclist = []
srclist += ['Sun','Moon']
if opts.cal != None:
    cat = a.cal.get_catalog(opts.cal, srclist, cutoff, catalogs)
else:
    cat = a.src.get_catalog(srclist, cutoff, catalogs)
print "Found %d sources in catalog(s) %s"%(len(cat),','.join(catalogs))
cat.compute(aa)
for src in cat.keys():
    if cat[src].alt<0 and not src=='Sun' and not src=='Moon': cat.pop(src)
src_pjys = n.array([pjys(cat[src],aa) for src in cat]).squeeze()
srcs = cat.keys()
elevations = n.array([cat[src].alt for src in cat]).squeeze()
flux_order = n.argsort(src_pjys)[::-1]
####################################################
# Print some useful things about this observation ###
#####################################################
print "="*80
print " "*20,"mysources!"
print "Date = ",aa.date
print "GPS Time = ",GPS_Time
print "Julian Date = ", aa.get_jultime()
print "local sidereal time = ",aa.sidereal_time()
print "input alt az =  %6.3f,%6.3f"%(alt,az)
print "alt az pointing = %6.3f,%6.3f"%(nearest_alt,nearest_az)
if opts.beamtype is 'MWA': print "beamformer setting = ",'[',','.join(map(str,bm_delays)),']'
print "Catalog = ",opts.cat
print "Approximate total flux = ",n.sum(src_pjys) - \
                pjys(cat['Sun'],aa) - pjys(cat['Moon'],aa)
        #NB: I leave Sun and Moon in catalog even if they are down but then I must be sure to subtract off their flux
        #from the total

###############################################3
# Print the source list #############  #
###############################################
print "-+"*45
print " "*20,"Percieved Catalog"
print "-"*80
print "Source Name\tFlux [Jy]\tPercieved Flux\t\tBeam [dB]\tAlt [d]\t\tAz[d]"
for i in flux_order: 
    src = cat[srcs[i]]
    print "%s\t%6.1f\t\t\t%8.3f\t%5.2f\t\t%6.2f\t\t%6.2f"%(src.src_name.ljust(10),
                            src.get_jys().squeeze(),
                            src_pjys[i],
                            dB(src_pjys[i]/src.get_jys().squeeze()),
                            180/n.pi*src.alt,
                            180/n.pi*src.az)
