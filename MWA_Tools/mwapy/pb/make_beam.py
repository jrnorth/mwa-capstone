import sys,os,logging,shutil,datetime,re,subprocess,math,tempfile,string,glob,platform
from optparse import OptionParser,OptionGroup
try:
    import astropy.io.fits as pyfits
    import astropy.wcs as pywcs
    _useastropy=True
except ImportError:
    import pywcs,pyfits
    _useastropy=False
import numpy,math,os
from mwapy import ephem_utils
from mwapy.pb import primary_beam
import mwapy

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('make_beam')
logger.setLevel(logging.WARNING)

######################################################################
def make_beam(filename, ext=0, delays=None, analytic_model=False,jones=False,
              precess=True,
              dipheight=primary_beam._DIPOLE_HEIGHT,
              dip_sep=primary_beam._DIPOLE_SEPARATION):
    """
    outputfiles=make_beam(filename, ext=0, delays=None, analytic_model=False,jones=False
    dipheight=primary_beam._DIPOLE_HEIGHT,
    dip_sep=primary_beam._DIPOLE_SEPARATION)
    """

    if jones and analytic_model:
        logger.warning('Cannot compute Jones matrix for analytic model: using advanced model...')
        analytic_model=False

    if delays is None:
        delays=[0]*16
    if len(delays) != 16:
        logger.error('Require 16 delays but %d supplied' % len(delays))
        return None

    try:
        f=pyfits.open(filename)
    except IOError,err:
        logger.error('Unable to open %s for reading\n%s', filename,err)
        return None
    if isinstance(ext,int):
        if len(f)<ext+1:
            logger.error('FITS file %s does not have extension %d' % (filename,ext))
            return None
    elif isinstance(ext,str):
        for extnum in xrange(len(f)):
            if ext.upper() == f[extnum].name:
                logger.info('Found matching extension %s[%d] = %s' % (filename,extnum,ext))
                ext=extnum
                break

    h=f[ext].header

    wcs=pywcs.WCS(h)

    naxes=h['NAXIS']

    if 'HPX' in h['CTYPE1']:
        logger.error('Cannot deal with HPX coordinates')
        return None

    freqfirst=True
    nfreq=1
    df=0
    # try  order  RA,Dec,Freq,Stokes
    if not 'RA' in h['CTYPE1']:
        logger.error('Coordinate 1 should be RA')
        return None
    if not 'DEC' in h['CTYPE2']:
        logger.error('Coordinate 1 should be DEC')
        return None
    if not 'FREQ' in h['CTYPE3']:
        freqfirst=False
        if not 'FREQ' in h['CTYPE4']:
            logger.error('Coordinate 3 or 4 should be FREQ')
            return None
    if freqfirst:
        logger.info('axis 3 is FREQ, axis 4 is STOKES')
        nfreq=h['NAXIS3']  # read number of frequency channels
        df=h['CDELT3']  # read frequency increment
    else:
        logger.info('axis 3 is STOKES, axis 4 is FREQ')
        nfreq=h['NAXIS4']
        df=h['CDELT4']
    logger.info('Number of frequency channels = ' + str(nfreq))
    # construct the basic arrays
    x=numpy.arange(1,h['NAXIS1']+1)
    y=numpy.arange(1,h['NAXIS2']+1)
    # assume we want the first frequency
    # if we have a cube this will have to change
    ff=1
    #X,Y=numpy.meshgrid(x,y)
    Y,X=numpy.meshgrid(y,x)

    Xflat=X.flatten()
    Yflat=Y.flatten()
    FF=ff*numpy.ones(Xflat.shape)
    Tostack=[Xflat,Yflat,FF]
    for i in xrange(3,naxes):
        Tostack.append(numpy.ones(Xflat.shape))
    pixcrd=numpy.vstack(Tostack).transpose()

    try:
        # Convert pixel coordinates to world coordinates
        # The second argument is "origin" -- in this case we're declaring we
        # have 1-based (Fortran-like) coordinates.
        if _useastropy:
            sky = wcs.wcs_pix2world(pixcrd, 1)
        else:
            sky = wcs.wcs_pix2sky(pixcrd, 1)

    except Exception, e:
        logger.error('Problem converting to WCS: %s' % e)
        return None

    # extract the important pieces
    ra=sky[:,0]
    dec=sky[:,1]
    if freqfirst:
        freq=sky[:,2]
    else:
        freq=sky[:,3]
    freq=freq[numpy.isfinite(freq)][0]
    if nfreq>1:
        frequencies=numpy.arange(nfreq)*df+freq
    else:
        frequencies=numpy.array([freq])

    # and make them back into arrays
    RA=ra.reshape(X.shape)
    Dec=dec.reshape(Y.shape)

    # get the date so we can convert to Az,El
    try:
        d=h['DATE-OBS']
    except:
        logger.error('Unable to read observation date DATE-OBS from %s' % filename)
        return None
    if '.' in d:
        d=d.split('.')[0]
    dt=datetime.datetime.strptime(d,'%Y-%m-%dT%H:%M:%S')
    mwatime=ephem_utils.MWATime(datetime=dt)
    logger.info('Computing for %s' % mwatime)


    if precess:
        RAnow,Decnow=ephem_utils.precess(RA,Dec,2000,mwatime.epoch)
    else:
        RAnow,Decnow=RA,Dec

    HA=float(mwatime.LST)-RAnow
    mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]
    Az,Alt=ephem_utils.eq2horz(HA,Decnow,mwa.lat)
    # go from altitude to zenith angle
    theta=(90-Alt)*math.pi/180
    phi=Az*math.pi/180

    tempY = numpy.zeros(f[ext].data.shape)  # copy to prevent rY from overwriting rX in the loop below
    for freqindex in xrange(len(frequencies)):
        try:
            if analytic_model:
                rX,rY=primary_beam.MWA_Tile_analytic(theta, phi,
                                                     freq=frequencies[freqindex], delays=delays,
                                                     dipheight=dipheight, dip_sep=dip_sep,
                                                     zenithnorm=True,
                                                     power=True)
            else:
                if not jones:
                    rX,rY=primary_beam.MWA_Tile_advanced(theta, phi,
                                                         freq=frequencies[freqindex], delays=delays, zenithnorm=True,
                                                         power=True)
                else:
                    J=primary_beam.MWA_Tile_advanced(theta, phi,
                                                     freq=frequencies[freqindex],
                                                     delays=delays, zenithnorm=True, jones=True)

                
        except Exception, e:
            print e
            logger.error('Problem creating primary beam: %s' % e)
            return None
        logger.info('Created primary beam for %.2f MHz and delays=%s' % (frequencies[freqindex]/1.0e6,
                                                                         ','.join([str(x) for x in delays])))

        if not jones:
            if freqfirst:
                f[ext].data[0,freqindex]=rX.transpose()
                tempY[0,freqindex]=rY.transpose()
            else:
                f[ext].data[freqindex,0]=rX.transpose()
                tempY[freqindex,0]=rY.transpose()


    if platform.__dict__.has_key('python_version'):
        pyver=platform.python_version()
    else:
        pyver='0.0'
    f[ext].header.set('PYVER',pyver,
                      'PYTHON Version number')            
    if pyfits.__dict__.has_key('__version__'):
        pyfitsver=pyfits.__version__
    else:
        pyfitsver='0.0'
    f[ext].header.set('PYFITS',pyfitsver,'PYFITS Version number')

    if pywcs.__dict__.has_key('__version__'):
        pywcsver=pyfits.__version__
    else:
        pywcsver='0.0'
    f[ext].header.set('PYWCS',pywcsver,
                      'PYWCS Version number')
    f[ext].header.set('DIPHT',dipheight,'[m] Dipole height')
    f[ext].header.set('DIPSP',dip_sep,'[m] Dipole separation')
    f[ext].header.set('MWAVER',mwapy.__version__,'MWAPY Version')

    if analytic_model:
        f[ext].header.set('BEAMMODL','ANALYTIC','Primary beam model')
    else:
        f[ext].header.set('BEAMMODL','SUJINTO14','Primary beam model')

    if jones:
        root=os.path.splitext(filename)[0]
        outnames=[]
        pols=[['XX',-5,0,0],
              ['XY',-7,0,1],
              ['YX',-6,1,0],
              ['YY',-8,1,1]]
        for p in pols:            
            if freqfirst:
                f[ext].data[0,freqindex] = J[:,:,p[2],p[3]].transpose().real
                f[ext].header['CRVAL4']=p[1]
            else:
                f[ext].data[freqindex,0] = J[:,:,p[2],p[3]].transpose().real
                f[ext].header['CRVAL3']=p[1]
            f[ext].header.set('POLN', p[0] + '-real')
            outname='%s_beam%sr.fits' % (root,p[0])
            if os.path.exists(outname):
                os.remove(outname)
            f[ext].writeto(outname)
            logger.info('%s-real beam written to %s' % (p[0],outname))
            outnames.append(outname)
            
            if freqfirst:
                f[ext].data[0,freqindex] = J[:,:,p[2],p[3]].transpose().imag
                f[ext].header['CRVAL4']=p[1]
            else:
                f[ext].data[freqindex,0] = J[:,:,p[2],p[3]].transpose().imag
                f[ext].header['CRVAL3']=p[1]
            f[ext].header.set('POLN', p[0] + '-imag')
            outname='%s_beam%si.fits' % (root,p[0])
            if os.path.exists(outname):
                os.remove(outname)
            f[ext].writeto(outname)
            logger.info('%s-imag beam written to %s' % (p[0],outname))
            outnames.append(outname)
        return outnames


    # see Greisen & Calabretta 2002, 395, 1061
    # Table 7
    # I=1
    # XX=-5
    # YY=-6
    # XY=-7
    # YX=-8
    if freqfirst:
        f[ext].header['CRVAL4']=-5.0
    else:
        f[ext].header['CRVAL3']=-5.0
    root=os.path.splitext(filename)[0]
    outname=root + '_beamXX' + '.fits'
    outnames=[outname]
    if os.path.exists(outname):
        os.remove(outname)
    f[ext].writeto(outname)
    logger.info('XX beam written to %s' % outname)

    if freqfirst:
        f[ext].data[0,:] = tempY[0,:]
    else:
        f[ext].data[:,0] = tempY[:,0]
    if freqfirst:
        f[ext].header['CRVAL4']=-6.0
    else:
        f[ext].header['CRVAL3']=-6.0
    outname=root + '_beamYY' + '.fits'
    if os.path.exists(outname):
        os.remove(outname)
    f[ext].writeto(outname)
    outnames.append(outname)
    logger.info('YY beam written to %s' % outname)

    return outnames
