import pyfits
import getopt,sys,os,logging,shutil,datetime,re,subprocess,math,tempfile,string,glob
import numpy

##################################################
class FITSImage:
##################################################
    """
    A class for FITS images generated from 32T data
    """

    ##################################################
    def __init__(self, filename=None, fake=None):
        """
        __init__self, filename=None, fake=None)
        """
        
        if (filename is not None and not os.path.exists(filename)):
            logger.error('Cannot access FITS file %s',filename)
            return None

        self.filename=filename
        self.fake=fake

    ##################################################
    def xy2rd(self, x, y, ignoreprojection=False):
        """
        ra,dec=xy2rd(self,x,y, ignoreprojection=False)
        converts from pixel coordinates x and y to RA and Dec
        x and y can be floats, lists, or ndarrays
        RA and Dec are returned in degrees
        if ignoreprojection, will ignore projection keywords PV2_1, PV2_2
        """

        if (self.filename is None):
            logger.error('Filename must be defined')
            return None
        if (not os.path.exists(self.filename)):
            logger.error('Cannot access FITS file %s',self.filename)
            return None
        hdulist=pyfits.open(self.filename)
        return _xy2rd(hdulist[0].header, x, y, ignoreprojection=ignoreprojection)

    ##################################################
    def rd2xy(self, r, d, ignoreprojection=False):
        """
        x,y=rd2xy(self,r,d, ignoreprojection=False)
        converts from RA and Dec (in degrees) to pixel coordinates x and y 
        RA and Dec can be floats, lists, or ndarrays
        if ignoreprojection, will ignore projection keywords PV2_1, PV2_2
        """

        if (self.filename is None):
            logger.error('Filename must be defined')
            return None,None
        if (not os.path.exists(self.filename)):
            logger.error('Cannot access FITS file %s',self.filename)
            return None,None
        hdulist=pyfits.open(self.filename)
        return _rd2xy(hdulist[0].header, r, d, ignoreprojection=ignoreprojection)

    ##################################################
    def min(self):
        """
        m=min(self)
        """
        if (self.filename is None):
            logger.error('Filename must be defined')
            return None
        if (not os.path.exists(self.filename)):
            logger.error('Cannot access FITS file %s',self.filename)
            return None
        f=pyfits.open(self.filename)
        D=f[0].data.flatten()
        return numpy.min(D)
    ##################################################
    def max(self):
        """
        m=max(self)
        """
        if (self.filename is None):
            logger.error('Filename must be defined')
            return None
        if (not os.path.exists(self.filename)):
            logger.error('Cannot access FITS file %s',self.filename)
            return None
        f=pyfits.open(self.filename)
        D=f[0].data.flatten()
        return numpy.max(D)

    ##################################################
    def median(self):
        """
        m=median(self)
        """
        if (self.filename is None):
            logger.error('Filename must be defined')
            return None
        if (not os.path.exists(self.filename)):
            logger.error('Cannot access FITS file %s',self.filename)
            return None
        f=pyfits.open(self.filename)
        D=f[0].data.flatten()
        return numpy.median(D)

    ##################################################
    def mean(self):
        """
        m=mean(self)
        """
        if (self.filename is None):
            logger.error('Filename must be defined')
            return None
        if (not os.path.exists(self.filename)):
            logger.error('Cannot access FITS file %s',self.filename)
            return None
        f=pyfits.open(self.filename)
        D=f[0].data.flatten()
        return numpy.mean(D)

    ##################################################
    def std(self):
        """
        m=std(self)
        """
        if (self.filename is None):
            logger.error('Filename must be defined')
            return None
        if (not os.path.exists(self.filename)):
            logger.error('Cannot access FITS file %s',self.filename)
            return None
        f=pyfits.open(self.filename)
        D=f[0].data.flatten()
        return numpy.std(D)

    ##################################################
    def quantile_std(self):
        """
        m=quantile_std(self)
        """
        if (self.filename is None):
            logger.error('Filename must be defined')
            return None
        if (not os.path.exists(self.filename)):
            logger.error('Cannot access FITS file %s',self.filename)
            return None
        f=pyfits.open(self.filename)
        D=f[0].data.flatten()
        return _quantile_std(D)

    ##################################################
    def iterstat(self,maxiter=10,clip=3,tol=1e-2,min=None,max=None,stat="mean"):
        """
        [mn,std,n,lowused,hiused,iters]=iterstat(self,maxiter=10,clip=3,tol=1e-2,min=None,max=None,stat="mean")
        """
        if (self.filename is None):
            logger.error('Filename must be defined')
            return None
        if (not os.path.exists(self.filename)):
            logger.error('Cannot access FITS file %s',self.filename)
            return None
        f=pyfits.open(self.filename)
        D=f[0].data.flatten()
        return _iterstat(D,maxiter,clip,tol,min,max,stat)

    ##################################################
    def printstatistics(self):
        """
        median,stdev,min,max=printstatistics(self)
        """
        m=self.median()
        s=self.quantile_std()
        mn=self.min()
        mx=self.max()
        #logger.info('# Image Median=%.3g\n# Image Stdev=%.3g\n# Image Min=%.3g\n# Image Max=%.3g' % (m,s,mn,mx))
        print '# Image Median=%.3g\n# Image Stdev=%.3g\n# Image Min=%.3g\n# Image Max=%.3g' % (m,s,mn,mx)
        return m,s,mn,mx

    ##################################################
    def updateheader(self, extn=0, key=None, value=None, comment=None):
        """
        updateheader(self, extn=0, key=None, value=None, comment=None)
        """

        if (not key):
            logger.error('Must specify key for header update')
            return None
        if (not value):
            logger.error('Must specify value for header update')
            return None
        if (self.filename is None):
            logger.error('Filename must be defined')
            return None
        if (not os.path.exists(self.filename)):
            logger.error('Cannot access FITS file %s',self.filename)
            return None
        if (not type(key) == type(value)):
            logger.error('Type of key argument (%s,%s) must be the same as type of value argument (%s,%s)',
                         key,type(key),value,type(value))
            return None
        f=pyfits.open(self.filename,'update')
        if (extn >= len(f)):
            logger.error('Specified extension %d is greater than number of extensions in file %d',
                         extn,len(f))
            return None
        if not (isinstance(key,list) or isinstance(value,list)):
            f[extn].header.update(key,value,comment)
        else:            
            if (len(key) != len(value)):
                logger.error('Size of keys (%d) must be equal to size of values (%d)',
                             len(key),len(value))
                return None
            if (comment):
                if (len(key) != len(value)):
                    logger.error('Size of keys (%d) must be equal to size of comments (%d)',
                                 len(key),len(comment))
                    return None
                for (k,v,c) in zip(key,value,comment):
                    f[extn].header.update(k,v,c)
            else:
                for (k,v) in zip(key,value):
                    f[extn].header.update(k,v)
        f.flush(output_verify='fix')
        f.close()
        return 1

###############################################
def _quantile_std(x):
    """
    std=quantile_std(x)
    x is numpy.array or masked array
    computes standard deviation as (q75-q25)/1.35
    where q75/q25 are the 75 and 25 percent quantiles
    """

    if (isinstance(x,numpy.ma.masked_array)):
        x=x.data[(1-x.mask).nonzero()]
    n=len(x)
    if (n==0):
        # no un-masked items remain
        return numpy.nan
    y=x.copy()
    y.sort()
    # DLK
    # should probably use a better version of this
    if (n % 4.0 != 0):
        q25=y[n/4]
        q75=y[3*n/4]
    else:
        q25=0.5*(y[n/4]+y[n/4+1])
        q75=0.5*(y[3*n/4]+y[3*n/4+1])
    return (q75-q25)/1.35

###############################################
def mergefitsfiles(outfitsname, filelist, name_it):
        """
        mergefitsfiles(outfitsname, filelist)
        """
        fitsout=pyfits.HDUList()
        count = 0
        for filename in filelist:
            new_names= name_it[count]     
            fitsin=pyfits.open(filename)
            fitsimage=pyfits.ImageHDU(fitsin[0].data, fitsin[0].header, name=new_names)
            fitsout.append(fitsimage)
            count = count + 1
        if (os.path.exists(outfitsname)):
            os.remove(outfitsname)
        fitsout.verify(option='silentfix')
        fitsout.writeto(outfitsname)
        return 1
######################################################
def _xy2rd(header, x, y, ignoreprojection=False):
    """
    ra,dec=_xy2rd(header,x,y, ignoreprojection=False)
    needs a FITS header with appropriate keywords
    converts from pixel coordinates x and y to RA and Dec
    x and y can be floats, lists, or ndarrays
    RA and Dec are returned in degrees
    if ignoreprojection, will ignore projection keywords PV2_1, PV2_2
    """

    if (not header):
        logger.error('Header must be defined')
        return None
    if (ignoreprojection):
        header=header.copy()
        try:
            del header['PV2_1']
            del header['PV2_2']
        except KeyError:
            logger.error('Unable to delete projection keywords for %s',self.filename)
    # there's got to be a better way to do this
    if isinstance(x,int):
        x=float(x)
    if isinstance(y,int):
        y=float(y)
    if (not x.__class__ == y.__class__):
        logger.error('x (%s) and y (%s) must be the same type',x.__class__,y.__class__)
        return None


    # leave the spectral/polarization axes out of it
    try:
        proj=wcs.Projection(header).sub(nsub=2)
    except KeyError, err:
        logger.error('Unable to access necessary header keywords for astrometry:\n',err)
        return None
    try:
        world=proj.toworld((x,y))
    except wcs.WCSinvalid:
        return None,None
    return world

##########################################
def ct2lst_mwa(yr,mn,dy,UT):
    """
    LST=ct2lst_mwa(yr,mn,dy,UT)
    convert from local time to LST (in hours)
    give yr,mn,dy,UT of time to convert
    assumes MWA site
    """
    mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]
    observer=ephem.Observer()
    observer.long=mwa.long/ephem_utils.DEG_IN_RADIAN
    observer.lat=mwa.lat/ephem_utils.DEG_IN_RADIAN
    observer.elevation=mwa.elev
    s=str(UT)
    if (s.count(':')>0):
        # it's hh:mm:ss
        # so leave it
        UTs=UT
    else:
        UTs=ephem_utils.dec2sexstring(UT,digits=0,roundseconds=0)
    observer.date='%d/%d/%d %s' % (yr,mn,dy,UTs)
    lst=observer.sidereal_time()*ephem_utils.HRS_IN_RADIAN
    return lst

#############################################
def dateobs2gps(dateobs):
    """ takes a FITS date-obs string
    YYYY-MM-DDThh:mm:ss
    and converts to gps seconds
    """
    date,ut=dateobs.split('T')
    yr,mn,dy=date.split('-')
    hour,min,sec=ut.split(':')
    UT=float(hour)+float(min)/60.0+float(sec)/3600.0
    MJD=ephem_utils.cal_mjd(int(yr),int(mn),int(dy))

    gps=ephem_utils.calcGPSseconds(MJD,UT)
    return gps
###############################################################################
### Sort out the FITS headers #######

#images = ['f_all_PicA_I.fits','f_all_PicA_XX.fits','f_all_PicA_YY.fits']
#current_stokes = ['I','XX','YY']
#for i in range(len(images)):
#        print 'Updating header in '+images[i]
#        fitsimage=FITSImage(filename=images[i])
#	m,s,mn,mx=fitsimage.printstatistics()
#	fitsimage.updateheader(key=['IMAGEMED','IMAGESTD','IMAGEMIN','IMAGEMAX'],
#	                      value=[m,s,mn,mx],comment=['[Jy/beam] Image median','[Jy/beam] Image rms',
#	                                                 '[Jy/beam] Image minimum','[Jy/beam] Image maximum'])
#	fitsimage.updateheader(key=['STOKES'],value=[current_stokes[i]],comment=[''])
        ####################################
        ##### Get rid of some casa crap ####
        

####### Merge XX, YY and I files ###########

#totalfitsoutname='test_out.fits'
#filescreated = ['f_all_PicA_I.fits','f_all_PicA_XX.fits','f_all_PicA_YY.fits']
#mergefitsfiles(totalfitsoutname, filescreated, '')
#mergefitsfiles(totalfitsoutname, filescreated, stokes=['I','XX','YY'])

####### Generate primary beam map #######

#fitsoutname = 'YY_3C444_SolInt_71_test.fits'
#current_stokes = 'YY'
#fitsimage=FITSImage(filename=fitsoutname)
#beamvalue = fitsimage.generate_primarybeam(stokes=current_stokes, basename='1', suffix='1')

######### Combine XX and YY final PB maps ##############
# Do same as above 


