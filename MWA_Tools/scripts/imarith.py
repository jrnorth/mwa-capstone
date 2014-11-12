#!/usr/bin/env python
"""
Can evaluate arithmatic expressions involving FITS files
example:

imarith.py -i GP000_l21.0_b0_f93-psf.fits,l0_b0_f121-psf.fits -o test.fits -e 'im0+im1' -v
Evaluating GP000_l21.0_b0_f93-psf.fits[0]+l0_b0_f121-psf.fits[0]
Wrote test.fits


"""

import os,pyfits,sys,re
import numpy as n
from optparse import OptionParser
import mwapy

######################################################################
######################################################################

def main():
    usage="Usage: %prog -i image0.fits,image1.fits -o output.fits -e <expression\n"
    usage+='\tEvaluates expression involving images\n'
    parser = OptionParser(usage=usage,version=mwapy.__version__)
    parser.add_option('-i','--images',dest='images',default=None,
                      help='Input images (comma separated)')
    parser.add_option('-o','--output',dest='output',default=None,
                      help='Output image name')
    parser.add_option('-e','--expression',dest='expression',default=None,
                      help='Expression to calculate (first image is im0)')
    parser.add_option('-x','--xtension',dest='extension',default=0,
                      type='int',
                      help='FITS extension [default=%default]')
    parser.add_option('-v','--verbose',dest='verbose',default=False,
                      action='store_true',
                      help='Increase verbosity of output?')

    (options, args) = parser.parse_args()
    images=options.images.split(',')
    imagef=[]
    imagedata=[]
    prettyexpression=options.expression
    for i in xrange(len(images)):
        im=images[i]
        if not os.path.exists(im):
            print 'Could not open %s' % im
            sys.exit(1)
        prettyexpression=prettyexpression.replace('im%d' % (i),
                                                  im + ('[%d]' % options.extension))
        imagef.append(pyfits.open(im))
        imagedata.append(imagef[-1][options.extension].data)
    try:
        if options.verbose:
            print 'Evaluating %s' % prettyexpression
        result=eval(re.sub(r'im(\d+)',r'imagedata[\1]',options.expression))
    except:
        print "Could not evaluate expression:\n\t%s\n\t%s" % (options.expression,
                                                              prettyexpression)
        sys.exit(1)
    imagef[0][options.extension].data=result
    imagef[0][options.extension].header.add_history('Evaluated %s' % prettyexpression)

    if os.path.exists(options.output):
        os.remove(options.output)
    imagef[0].writeto(options.output)
    if options.verbose:
        print 'Wrote %s' % options.output


######################################################################

if __name__=="__main__":
    main()
