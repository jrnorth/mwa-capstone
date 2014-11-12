#!/usr/bin/env python

# Copy the RA and Dec from one fits file to another

import pyfits,math,sys
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-i", "--input", dest="infile",
                  help="Input file to change header")
parser.add_option("-t", "--template", dest="template", 
                  help="Template file from which to get new header")
parser.add_option("-o", "--output", dest="outfile",
                  help="Out filename; default=new.fits", default="new.fits")
(options, args) = parser.parse_args()

hdu_in=pyfits.open(options.infile)
hdr_in=hdu_in[0].header

hdu_tmp=pyfits.open(options.template)
hdr_tmp=hdu_tmp[0].header

hdr_in['CRVAL1']=hdr_tmp['CRVAL1']
hdr_in['CRVAL2']=hdr_tmp['CRVAL2']

hdu_in.writeto(options.outfile)

hdu_in.close()
hdu_tmp.close()
