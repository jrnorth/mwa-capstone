"""
This is an AIPY cal file. It provides hooks that allow users to overwrite basic AIPY functions with 
custom classes and methods.

In this example, the cal file defines the array by building an AntennArray object.  The beam of the 
array is defined using the mwapy.pb.mwapb module. It also acts as the interface between the 
generic_catalog file interpreter and AIPY catalog tasks like position and gain calculation.

Cal files may be kept anywhere in the PYTHONPATH.  The working directory is often an expedient choice.
I keep mine in ~/cals/.

DJacobs 27 Feb 2012


"""



import aipy as a, numpy as n,glob,ephem
#import bm_prms as bm
from mwapy.catalog import generic_catalog
import logging
from mwapy.pb import mwapb
#from mwacasa.pb import mwapb
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('mwa_32T_pb')

prms = {
    'loc':('-26:42:11.95','116:40:14.93'),
    'antpos':{ 0:[0,0,0]
    },    
}
def top2azalt(xyz):
    th_phi = a.coord.xyz2thphi(xyz)
    th,phi = th_phi
    alt = n.pi/2 - th
    az = n.pi/2 - phi
    th_phi[0],th_phi[1] = az,alt
    return th_phi

class MWATileBeam(a.phs.Beam):
    def __init__(self,freqs,pol,delays=None):
        a.phs.Beam.__init__(self,freqs)
        self.TileBGs = [mwapb.MWA_tile_gain(freq=freq,stokes=pol,delays=delays) for freq in freqs*1e9]
    def response(self,xyz):
        x,y,z = xyz
        az,el = top2azalt(xyz)
        az *= 180/n.pi
        el *= 180/n.pi
        return n.array([BG.calculate(az,el) for BG in self.TileBGs])
def get_aa(freqs,delays=None):
    '''Return the AntennaArray to be used for simulation.'''
    location = prms['loc']
    antennas = []
    nants = len(prms['antpos'])
    for pi in ('X','Y'):
        for i in prms['antpos'].keys():
            #beam = bm.prms['beam'](freqs,nside=32,lmax=20,mmax=20,deg=7)
            #beam = a.fit.Beam2DGaussian(freqs, xwidth=45*n.pi/180, ywidth=45*n.pi/180)
            pol = pi+pi
            beam = MWATileBeam(freqs,pol,delays=delays)
            #try: beam.set_params(bm.prms['bm_prms'])
            #except(AttributeError): pass
            pos = prms['antpos'][i]
            dly = 0.
            off = 0. 
            amp =  1. 
            #twist = prms['twist'][i]
            bp_r =  n.array([1])
            bp_i = n.array([0])
            #twist = prms['twist'][i]
            #if pi == 'y': twist += n.pi/2.
            antennas.append(
                a.fit.Antenna(pos[0],pos[1],pos[2], beam, phsoff=[dly,off],
                amp=amp, bp_r=bp_r, bp_i=bp_i, pointing=(0.,n.pi/2,0),
                lat=prms['loc'][0])
            )
    aa = a.fit.AntennaArray(prms['loc'], antennas)
    return aa

src_prms = {
    #'cyg':{ 'jys':10**4.038797, 'index': -0.712972, },
    #'cas': {
    #    'a1':.00087, 'a2':.00064, 'th':0,
    #    'jys':10**4.047758, 'index': -1.169779,
    #    #'jys':11334.8238655,'index': -1.254381,
    #},
    'Sun': {
        'ra':0,'dec':0,'jys': 37320, 'index':2.08, 'a1':.00540, 'a2':.00490, 'th':0,
    },
    'Moon': {
        'ra':0,'dec':0,'jys': 100, 'index':0, 'a1':.00540, 'a2':.00490, 'th':0,
    },
    'Jupiter': {
        'ra':0,'dec':0,'jys': 1000, 'index':0, 'a1':.00540, 'a2':.00490, 'th':0,
    },    
    #'vir':{ 'jys':10**3.056388, 'index':  -1.457298 , },
    #'crab':{ 'jys':10**3.172870, 'index':  -0.837350 , },
#    'her':{ 'jys':10**2.599899, 'index':  -1.345695 , },
#    'hyd':{ 'jys':10**2.474107, 'index':  0.668695 , },
}

def get_catalog(srcs=None, cutoff=None, catalogs=['helm','misc']):
    '''Return a catalog containing the listed sources.'''
#    custom_srcs = ['J1615-605','J1935-461','J2154-692','J2358-605']
    log.info("get_catalog")
    specials = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter',
    'Saturn', 'Uranus', 'Neptune']
    srclist =[]
    for c in catalogs:
        log.info("looking for %s in a local file"%(c,))
        this_srcs = generic_catalog.get_srcs(srcs=srcs,
              cutoff=cutoff,catalogs=[c])
        if len(this_srcs)==0:
            log.warning("no sources found with genericfile, trying built in catalog")
            tcat = a.src.get_catalog(srcs=srcs, 
                   cutoff=cutoff, catalogs=[c])
            srclist += [tcat[src] for src in tcat]
        else: srclist += this_srcs
    #test bit. make all source indexes 0
    #for i in range(len(srclist)):
    #    srclist[i].index=0
    
    cat = a.fit.SrcCatalog(srclist)
    #Add specials.  All fixed radio sources must be in catalog, for completeness
    if not srcs is None:
        for src in srcs:
            if src in src_prms.keys():
                if src in specials:
                    cat[src] = a.fit.RadioSpecial(src,**src_prms[src])
    return cat

if __name__=='__main__':
    import sys, numpy as n
    if len(sys.argv)>1:
        print "loading catalog: ",sys.argv[1]
        logging.basicConfig(level=logging.DEBUG)
        cat = get_catalog(catalogs=[sys.argv[1]])
        names = [cat[src].src_name for src in cat]
        print "loaded",len(names)," sources"
        flx = [cat[src]._jys for src in cat]
        aa = get_aa(n.array([0.15]))
        aa.set_jultime(2455455.38225)
        cat.compute(aa)
        flx = cat.get_jys()
        if len(sys.argv)>=3:
            for src in sys.argv[2:]:
                aa.set_jultime(a.phs.ephem2juldate(aa.next_transit(cat[src])))
                aa.update()
                cat.compute(aa)
                print cat[src].src_name,cat[src].get_jys()
                print 'resp=',aa[0].bm_response(cat[src].get_crds('top'))
        print "brightest source in catalog"
        print names[n.argwhere(flx==n.max(flx)).squeeze()[0]],n.max(flx)
        log.info("loaded %d items from %s"%(len(cat),sys.argv[1]))
        try: assert([cat[src].e_S_nu for src in cat])
        except(AttributeError): print "this catalog does not have flux errors"
