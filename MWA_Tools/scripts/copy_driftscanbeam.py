#! /usr/bin/env python

"""

Copies the primary beams from one drift-scan observation to another

Example:
copy_driftscanbeam.py -t ../../../2014Apr/fields-2014-apr+16/1082717536_W_bm1.0_I.fits -v 1070373104_W_bm1.0_I.fits 

Requires that the images sizes and delay settings are the same
"""


import os,numpy,sys,shutil,time,math
from astropy.io import fits as pyfits
from astropy import wcs as pywcs
from optparse import OptionParser
import logging

logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('copy_driftscanbeam')
logger.setLevel(logging.WARNING)



usage="Usage: %prog [options] <images>\n"
usage+="\tCopies the primary beams from one drift-scan observation to another\n"
usage+="\tExample:\n"
usage+="\t\tcopy_driftscanbeam.py -t ../../../2014Apr/fields-2014-apr+16/1082717536_W_bm1.0_I.fits -v 1070373104_W_bm1.0_I.fits \n"
usage+="\tRequires that the images sizes and delay settings are the same\n"

parser = OptionParser(usage=usage)
parser.add_option('-t','--template',dest='image',default=None,
                  help='Template image name')
parser.add_option('-i','--i',dest='I',default='_beamI',
                  help='Suffix for I beam [default=%default]')
parser.add_option('-x','--xx',dest='XX',default='_beamXX',
                  help='Suffix for XX beam [default=%default]')
parser.add_option('-y','--yy',dest='YY',default='_beamYY',
                  help='Suffix for YY beam [default=%default]')
parser.add_option('-v','--verbose',action="store_true",
                  dest="verbose",default=False,
                  help="Increase verbosity of output")

(options, args) = parser.parse_args()
if (options.verbose):
    logger.setLevel(logging.INFO)

images=args

if options.image is None:
    logger.error('Must supply template image')
    sys.exit(1)

base,ext=os.path.splitext(options.image)
beamXX=base + options.XX + ext
beamYY=base + options.YY + ext
beamI=base + options.I + ext
doX=True
doY=True
doI=True
if not os.path.exists(beamXX):
    logger.warning('XX beam %s does not exist' % beamXX)
    doX=False
if not os.path.exists(beamYY):
    logger.warning('YY beam %s does not exist' % beamYY)
    doY=False
if not os.path.exists(beamI):
    logger.warning('I beam %s does not exist' % beamYY)
    doI=False
if not (doX or doY or doI):
    logger.error('No beams exist')
    sys.exit(1)


fX,fY,fI=None,None,None
for image in images:
    if doX:
        fX=pyfits.open(beamXX)
    if doY:
        fY=pyfits.open(beamYY)
    if doI:
        fI=pyfits.open(beamI)
    if not os.path.exists(image):
        logger.error('Image %s does not exist' % image)
        sys.exit(1)
    f=pyfits.open(image)

    if not f[0].header['NAXIS1'] == fX[0].header['NAXIS1'] and f[0].header['NAXIS2'] == fX[0].header['NAXIS2']:
        logger.error('Image sizes do not match: template is %dx%d, while input image is %dx%d' % (
                fX[0].header['NAXIS1'],fX[0].header['NAXIS2'],
                f[0].header['NAXIS1'],f[0].header['NAXIS2']))
        sys.exit(1)
    delays0=numpy.array(map(int,fX[0].header['DELAYS'].split(',')))
    delays=numpy.array(map(int,f[0].header['DELAYS'].split(',')))
    if not (delays==delays0).all():
        logger.error('Delays do not match:\n\ttemplate is %s\n\tinput image is %s' % (delays0,delays))
        sys.exit(1)
    for k in f[0].header.keys():
        if fX is not None:
            try:
                fX[0].header[k]=f[0].header[k]
            except:
                pass
        if fY is not None:
            try:
                fY[0].header[k]=f[0].header[k]
            except:
                pass
        if fI is not None:
            try:
                fI[0].header[k]=f[0].header[k]            
            except:
                pass
    base,ext=os.path.splitext(image)
    beamXXout=base + options.XX + ext
    beamYYout=base + options.YY + ext
    beamIout=base + options.I + ext
    if doX:
        fX[0].header['ORIGNAME']=beamXX
        if os.path.exists(beamXXout):
            os.remove(beamXXout)
        fX.writeto(beamXXout)
        logger.info('Wrote %s' % beamXXout)
    if doY:
        fY[0].header['ORIGNAME']=beamYY
        if os.path.exists(beamYYout):
            os.remove(beamYYout)
        fY.writeto(beamYYout)
        logger.info('Wrote %s' % beamYYout)
    if doI:
        fI[0].header['ORIGNAME']=beamI
        if os.path.exists(beamIout):
            os.remove(beamIout)
        fI.writeto(beamIout)
        logger.info('Wrote %s' % beamIout)
    
    if fX is not None:
        fX.close()
    if fY is not None:
        fY.close()
    if fI is not None:
        fI.close()
