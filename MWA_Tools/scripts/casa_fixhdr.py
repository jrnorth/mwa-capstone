# Add PV2_1 and PV2_2 to casa images

from math import *
from imhead import *
from casa import measures as me
from casa import exportfits as exportfits
import pyfits, os

def casa_fixhdr(imagename):

  #---------------------------------------------------------------------#
  # importing slalib for this one function is kinda expensive
  # Kudos to P.T. Wallace (1987) for writing such enduring code
  def slaGmst(UT1):
    D2PI=2.0*pi
    S2R=0.7272205216643039849e-04
    TU=(UT1-51544.5)/36525.0
  #  GMST at this UT
    SLAGMST=fmod(fmod(UT1,1.0)*D2PI+
  			   (24110.54841+
  			  (8640184.812866+
  			  (0.093104-6.2e-6*TU)*TU)*TU)*S2R,2.0*pi)
    return SLAGMST
  #---------------------------------------------------------------------#
  
  # Not robust to imagename having a trailing slash!
  fitsimage=os.path.splitext(imagename)[0]+'.fits'
  
  if os.path.exists('temp.fits'):
    os.remove('temp.fits')
  if os.path.exists(fitsimage):
    os.remove(fitsimage)

  # extract RA and DEC of phase centre
  
  ra=imhead(imagename=imagename,mode='get',hdkey='crval1')
  dec=imhead(imagename=imagename,mode='get',hdkey='crval2')
  ra_rad=ra['value']
  dec_rad=dec['value']
  
  # Use the observatory tools to find where the MWA lives
  # NB: .casarc must be up-to-date
  #lon_rad=me.observatory('MWA32T')['m0']['value']
  #lat_rad=me.observatory('MWA32T')['m1']['value']
  
  # Replacing with fixhdr versions, as I note a small difference between
  # its settings and the version in the observatory settings
  lon_rad=116.671*pi/180.0
  lat_rad=-26.703*pi/180.0
  # NB: The lack of precision in these hardcoded settings leads to an eventual
  # HA error of about 1", which presumably will lead to co-ordinate errors of
  # around the same magnitude.
  
  # Calculate the LST from the date and longitude
# They changed the format in CASA 4.2 (unstable)
  try: dateobs=imhead(imagename,mode='get',hdkey='date-obs')['value']
  except: dateobs=imhead(imagename,mode='get',hdkey='date-obs')
  t1 = me.epoch('utc', dateobs)
  
  # For some reason the LST returned by CASA is not the same as the one
  # calculated by fixhdr. I think it is because CASA doesn't properly distinguish
  # between GMST and UTC. Or at least, I couldn't find a way of doing so.
  # So, use manual calculations...
  gmst_rad=slaGmst(t1['m0']['value'])
  lst_rad=fmod(gmst_rad+lon_rad,2.0*pi)
  ha_rad=lst_rad-ra_rad
  
  # CASA calculations that didn't work
  #me.doframe(me.observatory('MWA32T'))
  #me.doframe(t1)
  #print t1
  #t2 = me.measure(t1,'LAST')
  #print('LST: '+qa.time(qa.sub(t2['m0'],qa.floor(t2['m0'])), prec=7)[0])
  #HA = LST - RA 
  #t3 = me.measure(t1,'HA',t2)
  #print('HA: '+qa.time(qa.sub(t3['m0'],qa.floor(t3['m0'])), prec=7)[0])
  #ha_rad=qa.convert(t3['m0'],'rad')['value']
  
  # calc the zenith angle (Z) and the parallactic angle (chi)
  
  cosZ=sin(lat_rad)*sin(dec_rad) + cos(lat_rad)*cos(dec_rad)*cos(ha_rad)
  tanZA=tan(acos(cosZ))
  chi_rad=atan2(cos(lat_rad)*sin(ha_rad),(sin(lat_rad)*cos(dec_rad))-cos(lat_rad)*sin(dec_rad)*cos(ha_rad))
  xi=tanZA*sin(chi_rad)
  eta=tanZA*cos(chi_rad)
  
  # fixhdr-style printing for comparison
  print '-----------------------'
  print 'RA (rad) {0:8.6f}'.format(ra_rad)
  print 'DEC (rad) {0:8.6f}'.format(dec_rad)
  print 'LON (rad) {0:8.6f}'.format(lon_rad)
  print 'LAT (rad) {0:8.6f}'.format(lat_rad)
  print 'LST (from JD and LON) (rad) {0:8.6f}'.format(lst_rad)
  print 'JD {0:8.6f}'.format(t1['m0']['value']+2400000.5)
  print 'hour is {0:8.6f}'.format(ha_rad)
  print '-----------------------'
  
  # When CASA exports, it sets PV2_1 and _2 to zero, and you can't overwrite this by using imhead.
  # So, you need to export, THEN modify PV2s
  
  exportfits(imagename=imagename, fitsimage='temp.fits')

  hdu_in=pyfits.open('temp.fits')
  hdr_in=hdu_in[0].header

  hdr_in['PV2_1']=xi
  hdr_in['PV2_2']=eta
  
  hdu_in.writeto(fitsimage)
  hdu_in.close()
  
  os.remove('temp.fits')
  return fitsimage

if __name__ == "__main__":
    fitsimage=casa_fixhdr(imagename)
