#! /usr/bin/env python
"""

plock[pbtest]% python ~/mwa/bin/make_beam.py -f P00_w.fits -v
# INFO:make_beam: Computing for 2011-09-27 14:05:06+00:00
# INFO:make_beam: Created primary beam for 154.24 MHz and delays=0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
# INFO:make_beam: XX beam written to P00_w_beamXX.fits
# INFO:make_beam: YY beam written to P00_w_beamYY.fits

"""
import sys,os,logging,shutil,datetime,re,subprocess,math,tempfile,string,glob
from optparse import OptionParser,OptionGroup
import numpy,math,os
from mwapy.pb import primary_beam,make_beam
import mwapy
try:
    import astropy.io.fits as pyfits
except ImportError:
    import pyfits

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('make_beam')
logger.setLevel(logging.WARNING)

######################################################################
def main():

    usage="Usage: %prog [options]\n"
    usage+='\tMakes primary beams associated with a FITS image\n'
    parser = OptionParser(usage=usage,version=mwapy.__version__)
    parser.add_option('-f','--filename',dest="filename",default=None,
                      help="Create primary beam for <FILE>",metavar="FILE")
    parser.add_option('-e','--ext',dest='ext',type=str,default='0',
                      help='FITS extension name or number [default=%default]')
    parser.add_option('-m','--metafits',dest='metafits',default=None,
                      help="FITS file to get delays from (can be metafits)")
    parser.add_option('-d','--delays',dest="delays",default=None,
                      help="Beamformer delays to use; 16 comma-separated values")
    parser.add_option('--analytic',action="store_true",dest="analytic_model",default=False,
                      help="Use the old analytic dipole model, instead of the default Sutinjo 2014 model.")
    parser.add_option('--jones',dest='jones',default=False,
                      action='store_true',
                      help="Compute Jones matrix instead of power beam? [default=False]")    
    parser.add_option('--noprecess',action='store_false',
                      dest='precess',default=True,
                      help='Do not precess coordinates to current epoch (faster but less accurate) [default=False]')
    parser.add_option('--height',dest='height',default=primary_beam._DIPOLE_HEIGHT,
                      type=float,
                      help='Dipole height (m) (only an option for analytic beam model) [default=%default]')
    parser.add_option('--sep',dest='separation',default=primary_beam._DIPOLE_SEPARATION,
                      type=float,
                      help='Dipole separation (m) (only an option for analytic beam model) [default=%default]')
    parser.add_option('-v','--verbose',action="store_true",dest="verbose",default=False,
                      help="Increase verbosity of output")

    (options, args) = parser.parse_args()

    if (options.verbose):
        logger.setLevel(logging.INFO)

    try:
        extnum=int(options.ext)
        ext=extnum
    except:
        ext=options.ext
        pass
    if options.delays is not None:
        try:
            options.delays=[int(x) for x in options.delays.split(',')]
        except Exception,e:
            logger.error('Unable to parse beamformer delays %s: %s' % (options.delays,e))
            sys.exit(1)
    if options.metafits is not None:
        try:
            f=pyfits.open(options.metafits)
        except Exception,e:
            logger.error('Unable to open FITS file %s: %s' % (options.metafits,e))
            sys.exit(1)
        if not 'DELAYS' in f[0].header.keys():
            logger.error('Cannot find DELAYS in %s' % options.metafits)
            sys.exit(1)            
        options.delays=f[0].header['DELAYS']
        try:
            options.delays=[int(x) for x in options.delays.split(',')]
        except Exception,e:
            logger.error('Unable to parse beamformer delays %s: %s' % (options.delays,e))
            sys.exit(1)
            
    if options.filename is None:
        logger.error('Must supply a filename')
        sys.exit(1)

    out=make_beam.make_beam(options.filename, ext=ext, delays=options.delays,
                            analytic_model=options.analytic_model,
                            jones=options.jones,
                            precess=options.precess,
                            dipheight=options.height, dip_sep=options.separation)
    if out  is None:
        logger.error('Problem creating primary beams')
        sys.exit(1)
    

    sys.exit(0)
            
    

######################################################################

if __name__=="__main__":
    main()
