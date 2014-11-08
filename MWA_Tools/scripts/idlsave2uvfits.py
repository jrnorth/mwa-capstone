#!/scratch/partner678/MWA/bin/python
# -*- coding: utf-8 -*-
"""
Created on Fri Jun 20 14:06:19 2014

@author: bpindor
Converts IDL save files produced by UW FHD pipeline to UVFITS format
"""
import optparse
from astropy.io import fits
from scipy.io.idl import readsav
import sys,os
from numpy import zeros, shape, real, imag, arange

parser = optparse.OptionParser()

parser.add_option('-f', "--file_path", help="MANDATORY - Input filenames. Should be of the format [input]_(vis_(xx/yy)/params).sav  ")

parser.add_option('-o', "--output", help="Output filename:[output].uvfits ")

options, args = parser.parse_args()

print options.file_path

xx_datafile = options.file_path + '_vis_xx.sav'
yy_datafile = options.file_path + '_vis_yy.sav'
paramsfile = options.file_path + '_params.sav'

try:
    xx_data = readsav(xx_datafile)
except IOError, err:
    'Cannot open xx visbilities file %s\n',str(xx_datafile)
try:
    yy_data = readsav(yy_datafile)
except IOError, err:
    'Cannot open yy visbilities file %s\n',str(yy_datafile)
try:
    params = readsav(paramsfile)
except IOError, err:
    'Cannot open params file %s\n',str(paramsfile)
    
# syntax to READ parameter names??

p = params.params

uu = p['UU'][0]
vv = p['VV'][0]
ww = p['WW'][0]
baseline = p['BASELINE_ARR'][0]
time = p['TIME'][0]  

# Some slightly ugly parsing to get the mjd

mth = xx_data.obs['META_HDR']  
name_string = ((((mth[0])[6]).split())[1])
date_0  = float(name_string[14:21]) + 0.5
#date = time + date_0
date = time

# Actual visibility values

xx_visibilities = xx_data.vis_ptr
yy_visibilities = yy_data.vis_ptr

# Need to reformat visibilities info uvfits groups
# The dimensions of the visibility groups are [1,1,N_FREQ,N_POL,3 (re,im,weight)]


n_freq = shape(xx_visibilities)[1]
#n_freq = n_freq / 24 # FOR DEBUGGING

v_container = zeros((len(xx_visibilities),1,1,n_freq,4,3))
v_slice = zeros((1,1,n_freq,4,3))

# Load using loops. Is there a better way?
for i in range(len(xx_visibilities)):
    v_slice[0,0,:,0,0] = real(xx_visibilities[i,:n_freq])
    v_slice[0,0,:,0,1] = imag(xx_visibilities[i,:n_freq])
    v_slice[0,0,:,0,2] = 1.0
    v_slice[0,0,:,1,0] = real(yy_visibilities[i,:n_freq])
    v_slice[0,0,:,1,1] = imag(yy_visibilities[i,:n_freq])
    v_slice[0,0,:,1,2] = 1.0
    v_container[i] = v_slice
      
#uvparnames = ['UU','VV','WW','BASELINE_ARR','TIME']
uvparnames = ['UU','VV','WW','BASELINE_ARR','DATE']
parvals = [uu,vv,ww,baseline,date]
#pzeros = [0.0,0.0,0.0,0.0,date_0]
#pscales = [1.0] * 5


hdu10 = fits.GroupData(v_container,parnames=uvparnames,pardata=parvals,bitpix=-32)

#
hdu10 = fits.GroupsHDU(hdu10)

hdu10.header['CTYPE2'] = 'COMPLEX '
hdu10.header['CRVAL2'] = 1.0
hdu10.header['CRPIX2'] = 1.0
hdu10.header['CDELT2'] = 1.0

hdu10.header['CTYPE3'] = 'STOKES '
hdu10.header['CRVAL3'] = -5.0
hdu10.header['CRPIX3'] = 1.0
hdu10.header['CDELT3'] = -1.0


# Write header information. Not sure about central frequency value as
# it differs between ngas header and fhd value.
hdu10.header['CTYPE4'] = 'FREQ'
#hdu10.header['CRVAL4'] = xx_data.obs['FREQ_CENTER'][0] 
# 40khz offset for consistency with RTS outputs - to be verified
hdu10.header['CRVAL4'] = xx_data.obs['FREQ_CENTER'][0]  + 4.0e4
hdu10.header['CRPIX4'] = n_freq/2 + 1 # Freq bin corresponding to central freq

Bandwidth = float(((xx_data.obs['META_HDR'][0])[41]).split()[1])
delt_freq = (Bandwidth / n_freq) * 1e6
hdu10.header['CDELT4'] = delt_freq

 
hdu10.header['CTYPE5'] = 'RA'
hdu10.header['CRVAL5'] = xx_data.obs['ORIG_PHASERA'][0]
hdu10.header['OBJECT'] = 'MWA'
hdu10.header['OBSRA'] = xx_data.obs['ORIG_PHASERA'][0]
hdu10.header['OBSDEC'] = xx_data.obs['ORIG_PHASEDEC'][0]
hdu10.header['CTYPE6'] = 'DEC'
hdu10.header['CRVAL6'] = xx_data.obs['ORIG_PHASEDEC'][0]

# Write the parameters scaling explictly because they are omitted if default 1/0

hdu10.header['PSCAL1'] = 1.0
hdu10.header['PZERO1'] = 0.0
hdu10.header['PSCAL2'] = 1.0
hdu10.header['PZERO2'] = 0.0
hdu10.header['PSCAL3'] = 1.0
hdu10.header['PZERO3'] = 0.0
hdu10.header['PSCAL4'] = 1.0
hdu10.header['PZERO4'] = 0.0
hdu10.header['PSCAL5'] = 1.0
hdu10.header['PZERO5'] = date_0

#
# Create an hdu for the antenna table
#

n_tiles = 128

annames = [''] * n_tiles
nosta = arange(n_tiles) + 1
mntsta = [0] * n_tiles
staxof = [0] * n_tiles
poltya = ['X'] * n_tiles
polaa = [90.0] * n_tiles
polcala = [[0.0, 0.0, 0.0]] * n_tiles
poltyb = ['Y'] * n_tiles
polab = [0.0] * n_tiles
polcalb = [[0.0, 0.0, 0.0]] * n_tiles

stabxyz = [[0.0, 0.0, 0.0]] * n_tiles

col1 = fits.Column(name='ANNAME', format='8A', array=annames)
col2 = fits.Column(name='STABXYZ', format='3D', array=stabxyz) 
col3 = fits.Column(name='NOSTA', format='1J', array=nosta)
col4 = fits.Column(name='MNTSTA', format='1J', array=mntsta) 
col5 = fits.Column(name='STAXOF', format='1E', array=staxof) 
col6 = fits.Column(name='POLTYA', format='1A', array=poltya)
col7 = fits.Column(name='POLAA', format='1E', array=polaa) 
col8 = fits.Column(name='POLCALA', format='3E', array=polcala)
col9 = fits.Column(name='POLTYB', format='1A', array=poltyb) 
col10 = fits.Column(name='POLAB', format='1E', array=polab)
col11 = fits.Column(name='POLCALB', format='3E', array=polcalb) 

cols = fits.ColDefs([col1, col2,col3, col4,col5, col6,col7, col8,col9, col10,col11])
# This only works for astropy 0.4 which is not available from pip
#ant_hdu = fits.BinTableHDU.from_columns(cols)


ant_hdu = fits.new_table(cols)
ant_hdu.header['EXTNAME'] = 'AIPS AN'
ant_hdu.header['FREQ'] = xx_data.obs['FREQ_CENTER'][0] 
# Some spoofed antenna table headers, these may need correcting
ant_hdu.header['ARRAYX'] = -2557572.345962
ant_hdu.header['ARRAYY'] = 5091627.14195476
ant_hdu.header['ARRAYZ'] = -2856535.56228611
ant_hdu.header['GSTIAO'] = 331.448628115495
ant_hdu.header['DEGPDY'] = 360.985
ant_hdu.header['DATE'] = '2013-08-23T00:00:00.0'
ant_hdu.header['POLARX'] = 0.0
ant_hdu.header['POLARY'] = 0.0
ant_hdu.header['UT1UTC'] = 0.0
ant_hdu.header['DATUTC'] = 0.0
ant_hdu.header['TIMSYS'] = 'UTC  '
ant_hdu.header['ARRNAM'] = '     '
ant_hdu.header['NUMORB'] = 0
ant_hdu.header['NOPCAL'] = 3
ant_hdu.header['FREQID'] = -1
ant_hdu.header['IATUTC'] = 35.

# Create hdulist and write out file

hdulist = fits.HDUList(hdus=[hdu10,ant_hdu])
if options.output:
    outfile = options.output + '.uvfits'
else:
    outfile = 'idlsave.uvfits'

hdulist.writeto(outfile,clobber=True)

