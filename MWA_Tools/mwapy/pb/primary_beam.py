"""
$Rev: 4142 $:     Revision of last commit
$Author: dkaplan $:  Author of last commit
$Date: 2011-10-31 11:30:40 -0500 (Mon, 31 Oct 2011) $:    Date of last commit

"""

from mwapy import ephem_utils
import sys,bisect
import pyfits,numpy,math,logging
import os
import getopt
import mwa_tile

logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger(__name__)   # default logger level is WARNING

# dipole height in m
_DIPOLE_HEIGHT=0.278
# dipole separation in m
_DIPOLE_SEPARATION=1.1
# delay unit in s
_DELAY_INT=435.0e-12


#########
#########
def MWA_Tile_advanced(za, az, freq=100.0e6, delays=None, zenithnorm=True, power=True, jones=False):
    """
    Use the new MWA tile model from mwa_tile.py that includes mutual coupling
    and the simulated dipole response. Returns the XX and YY response to an
    unpolarised source.

    if jones=True, will return the Jones matrix instead

    delays should be a numpy array of size (2,16), although a (16,) list or a (16,) array will also be accepted    
    
    """
    if isinstance(delays,list):
        delays=numpy.array(delays)

    if delays.shape == (16,):
        try:
            delays=numpy.repeat(numpy.reshape(delays,(1,16)),2,axis=0)
        except:
            logger.error('Unable to convert delays (shape=%s) to (2,16)' % (delays.shape))
            return None
    assert delays.shape == (2,16), "Delays %s have unexpected shape %s" % (delays,delays.shape)
    
    logger.setLevel(logging.DEBUG)
    d = mwa_tile.Dipole(type='lookup') 
    logger.debug("Delays: "+str(delays))
    tile = mwa_tile.ApertureArray(dipoles=[d]*16)   # tile of identical dipoles
    j = tile.getResponse(az,za,freq,delays=delays)
    if jones:
        return j
    vis = mwa_tile.makeUnpolInstrumentalResponse(j,j)
    if not power:
        return (numpy.sqrt(vis[:,:,0,0].real),numpy.sqrt(vis[:,:,1,1].real))
    else:
        return (vis[:,:,0,0].real,vis[:,:,1,1].real)


######################################################################
# Based on code from Daniel Mitchel
# 2012-02-13
# taken from the RTS codebase
######################################################################
def MWA_Tile_analytic(za, az, freq=100.0e6, delays=None,
                      zenithnorm=True,
                      power=False,
                      dipheight=_DIPOLE_HEIGHT,
                      dip_sep=_DIPOLE_SEPARATION, 
                      delay_int=_DELAY_INT):

    """
    gainXX,gainYY=MWA_Tile_analytic(za, az, freq=100.0e6, delays=None, zenithnorm=True, power=True, dipheight=0.278, dip_sep=1.1, delay_int=435.0e-12)
    if power=False, then gains are voltage gains - should be squared for power
    otherwise are power
    
    za is zenith-angle in radians
    az is azimuth in radians, phi=0 points north
    freq in Hz, height, sep in m

    delays should be a numpy array of size (2,16), although a (16,) list or a (16,) array will also be accepted    

    """
    theta=za
    phi=az

    c=2.998e8
    # wavelength in meters
    lam=c/freq

    if (delays is None):
        delays=0

    if (isinstance(delays,float) or isinstance(delays,int)):
        delays=delays*numpy.ones((16))
    if (isinstance(delays,numpy.ndarray) and len(delays)==1):
        delays=delays[0]*numpy.ones((16))        
    if isinstance(delays,list):
        delays=numpy.array(delays)

    assert delays.shape == (2,16) or delays.shape == (16,), "Delays %s have unexpected shape %s" % (delays,delays.shape)
    if len(delays.shape)>1:
        delays=delays[0]

    # direction cosines (relative to zenith) for direction az,za
    projection_east=numpy.sin(theta)*numpy.sin(phi)
    projection_north=numpy.sin(theta)*numpy.cos(phi)
    projection_z=numpy.cos(theta)

    # dipole position within the tile
    dipole_north=dip_sep*numpy.array([1.5,1.5,1.5,1.5,0.5,0.5,0.5,0.5,-0.5,-0.5,-0.5,-0.5,-1.5,-1.5,-1.5,-1.5])
    dipole_east=dip_sep*numpy.array([-1.5,-0.5,0.5,1.5,-1.5,-0.5,0.5,1.5,-1.5,-0.5,0.5,1.5,-1.5,-0.5,0.5,1.5])
    dipole_z=dip_sep*numpy.zeros(dipole_north.shape)
    
    # loop over dipoles
    array_factor=0.0

    for i in xrange(4):
        for j in xrange(4):
            k=4*j+i
            # relative dipole phase for a source at (theta,phi)
            phase=numpy.exp((1j)*2*math.pi/lam*(dipole_east[k]*projection_east + dipole_north[k]*projection_north +
                                                dipole_z[k]*projection_z-delays[k]*c*delay_int))
            array_factor+=phase/16.0

    ground_plane=2*numpy.sin(2*math.pi*dipheight/lam*numpy.cos(theta))
    # make sure we filter out the bottom hemisphere
    ground_plane*=(theta<=math.pi/2)
    # normalize to zenith
    if (zenithnorm):
        ground_plane/=2*numpy.sin(2*math.pi*dipheight/lam)

    # response of the 2 tile polarizations
    # gains due to forshortening
    dipole_ns=numpy.sqrt(1-projection_north*projection_north)
    dipole_ew=numpy.sqrt(1-projection_east*projection_east)

    # voltage responses of the polarizations from an unpolarized source
    # this is effectively the YY voltage gain
    gain_ns=dipole_ns*ground_plane*array_factor
    # this is effectively the XX voltage gain
    gain_ew=dipole_ew*ground_plane*array_factor

    if power:
        return numpy.real(numpy.conj(gain_ew)*gain_ew), numpy.real(numpy.conj(gain_ns)*gain_ns)
    return gain_ew,gain_ns

