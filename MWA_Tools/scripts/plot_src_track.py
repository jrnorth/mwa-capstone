#! /usr/bin/env python
"""
Plots source trackes given input date range and source list
Author: Danny Jacobs
"""
import numpy as n, aipy as a, optparse, os, sys, ephem,logging
from pylab import *



def pjys(src,aa,pol='x'):
    src.compute(aa)
    crd = src.get_crds('top')
    bm = aa[0].bm_response(src.get_crds('top'),pol=pol)
    return src.jys*bm


o = optparse.OptionParser()
o.set_usage('mdlvis.py [options] *.uv')
o.set_description(__doc__)
a.scripting.add_standard_options(o, cal=True, src=True,ant=True,pol=True)
o.add_option('--startjd', dest='startjd', default=2454600., type='float',
    help='Julian Date to start observation if no input data to mimic.  Default is 2454600')
o.add_option('--endjd', dest='endjd', default=2454601., type='float',
    help='Julian Date to end observation if no input data to mimic.  Default is 2454601')

opts, args = o.parse_args(sys.argv[1:])
assert(opts.cal)
assert(opts.pol)
aa = a.cal.get_aa(opts.cal, n.array([0.15]))
srclist,cutoff,catalogs = a.scripting.parse_srcs(opts.src, opts.cat)
cat = a.cal.get_catalog(opts.cal, srclist, cutoff, catalogs)

print "found %d sources in catalog(s) %s"%(len(cat),','.join(catalogs))

times = n.linspace(opts.startjd,opts.endjd,60*5) #time interval hard-coded to 5 minutes

for srcname in cat:
    fluxes = []
    srcpositions = []
    for t in times:
        aa.set_jultime(t)
        src = cat[srcname]
        src.compute(aa)
        srcpos = src.get_crds('top',ncrd=3)
        srcpositions.append(srcpos)
        flux = pjys(src,aa,opts.pol)
#        print aa[0].bm_response(cat.get_crds('top')).shape
        fluxes.append(flux)
        #print flux.shape,srcpos.shape
        #sys.exit()
    srcpositions = n.array(srcpositions)
    fluxes = n.array(fluxes).squeeze()
    print fluxes.shape,srcpositions.shape
    plot(srcpositions[:,0],fluxes,label=srcname)
show()
