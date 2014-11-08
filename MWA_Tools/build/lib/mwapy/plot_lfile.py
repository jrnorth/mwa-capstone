import logging, sys, os, glob, string, re, urllib, math, time
from optparse import OptionParser
import numpy
import matplotlib
if not 'matplotlib.backends' in sys.modules:
    matplotlib.use('agg')
#import matplotlib.pyplot as pylab
import pylab

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('plot_lfile')
logger.setLevel(logging.WARNING)
            

######################################################################
def load_acdata(filename, ninputs=64, nchannels=768):
    """
    data=load_acdata(filename, ninputs=64, nchannels=768)
    returns a masked array with dimensions:
    (nintegrations, ninputs, nchannels)
    
    """

    if not os.path.exists(filename):
        logger.error('Cannot find L file %s' % filename)
        return None

    acsize=os.path.getsize(filename)
    logger.info("# AC size for %s: %d bytes" % (filename,acsize))
    nintegrations=int(acsize/(nchannels*ninputs*4))
    logger.info("# %s containts %d integrations" % (filename,nintegrations))

    if (acsize != nintegrations*nchannels*ninputs*4):
        logger.warning('(%d,%d,%d) predicts a size of %d bytes, but actual size is %d bytes' % (nintegrations,
                                                                                                ninputs,nchannels,
                                                                                                acsize))    
    try:
        fin=open(filename,'r')
        logger.info('# Opened L file: %s' % (filename))
    except:
        logger.error('Cannot open L file: %s' % filename)
        return None
    
    mask=numpy.zeros((nintegrations,ninputs,nchannels),dtype=numpy.bool)
    indata=numpy.ma.array(numpy.fromfile(file=fin,dtype=numpy.float32,
                                         count=nchannels*ninputs*nintegrations).reshape((nintegrations,ninputs,nchannels)),
                          mask=mask)
    
    mask[indata.data==0]=True
    return indata

######################################################################
def load_ccdata(filename, ninputs=64, nchannels=768):
    """
    data=load_ccdata(filename, ninputs=64, nchannels=768)
    returns a masked array with dimensions:
    (nintegrations, ninputs*(ninputs-1)/2, 2*nchannels)
    
    """

    if not os.path.exists(filename):
        logger.error('Cannot find L file %s' % filename)
        return None

    ccsize=os.path.getsize(filename)
    logger.info("# CC size for %s: %d bytes" % (filename,ccsize))
    nintegrations=int(ccsize/(nchannels*2*ninputs*(ninputs-1)/2*4))
    logger.info("# %s containts %d integrations" % (filename,nintegrations))

    if (ccsize != (nintegrations*nchannels*2*ninputs*(ninputs-1)/2*4)):
        logger.warning('(%d,%d,%d) predicts a size of %d bytes, but actual size is %d bytes' % (nintegrations,
                                                                                                ninputs,nchannels,
                                                                                                acsize))    
    try:
        fin=open(filename,'r')
        logger.info('# Opened L file: %s' % (filename))
    except:
        logger.error('Cannot open L file: %s' % filename)
        return None
    
    mask=numpy.zeros((nintegrations,ninputs*(ninputs-1)/2,2*nchannels),dtype=numpy.bool)
    indata=numpy.ma.array(numpy.fromfile(file=fin,dtype=numpy.float32,
                                         count=nchannels*2*ninputs*(ninputs-1)/2*nintegrations).reshape((nintegrations,ninputs*(ninputs-1)/2,2*nchannels)),
                          mask=mask)
    
    mask[indata.data==0]=True
    return indata

##################################################
def plot_acdata(data,root,level=1,title='',format='png'):
        """
        outputfiles=plot_acdata(data,level=1,title='',format='png'):

        plots the XX and YY amplitudes as a function of time, frequency, and antenna
        for each plot it averages over the other axes

        saves to files <root>_*.<format>

        requires pylab

        level=1: amplitude vs. (channel, antenna, time) averaging over other axes
        level=2: previous AND amplitude vs. (channel, time) for each antenna
        level=3: previous AND waterfall plots showing amplitude vs. channels and time for each antenna
        format is the graphics format for output (should be supported by matplotlib backend)

        """
            
        outputfiles=[]
        
        xxdata=data[:,::2,:]
        yydata=data[:,1::2,:]
        # mask out values that are 0, but are not masked otherwise
        ntimes=xxdata.shape[0]
        nchan=xxdata.shape[2]
        nants=xxdata.shape[1]


        # turn off tex for the text
        pylab.rc('text',usetex=False)        
        fig=pylab.figure()
        
        if (level >= 1):
            time=1+numpy.arange(ntimes)
            #fig=pylab.figure()
            fig.clf()
            fig.subplots_adjust(hspace=-0.0)
            ax1=fig.add_subplot(2,1,1)
            ax2=fig.add_subplot(2,1,2)
            zx=xxdata.mean(axis=2).mean(axis=1)
            zy=yydata.mean(axis=2).mean(axis=1)
            ax1.plot(time,zx,'b')
            ax2.plot(time,zy,'r')
            ax2.set_xlabel('Time (samples)')
            ax1.set_ylabel('XX Amplitude')
            ax2.set_ylabel('YY Amplitude')
            ax1.xaxis.set_ticklabels('')            
            ax1.set_title(title)
            fname='%s_time.%s' % (root,format)
            logger.info('# Saving amplitude vs. time to %s' % (fname))
            try:
                pylab.savefig(fname)
                outputfiles.append(fname)
            except RuntimeError,err:
                logger.error('Error saving figure: %s',err)                
            del ax1,ax2,time,zx,zy
            
            chans=1+numpy.arange(nchan)
            #fig=pylab.figure()
            fig.clf()
            fig.subplots_adjust(hspace=-0)
            ax1=fig.add_subplot(2,1,1)
            ax2=fig.add_subplot(2,1,2)
            zx=xxdata.mean(axis=0).mean(axis=0)
            zy=yydata.mean(axis=0).mean(axis=0)
            ax1.plot(chans,zx,'b')
            ax2.plot(chans,zy,'r')
            ax2.set_xlabel('Channel Number')
            ax1.set_ylabel('XX Amplitude')
            ax2.set_ylabel('YY Amplitude')                        
            ax1.xaxis.set_ticklabels('')
            ax1.set_title(title)
            fname='%s_channel.%s' % (root,format)
            logger.info('# Saving amplitude vs. channel to %s' % (fname))
            try:
                pylab.savefig(fname)
                outputfiles.append(fname)
            except RuntimeError,err:
                logger.error('Error saving figure: %s',err)                

            del ax1,ax2,chans,zx,zy
        
            ants=1+numpy.arange(nants)
            #fig=pylab.figure()
            fig.clf()
            fig.subplots_adjust(hspace=-0.0)
            ax1=fig.add_subplot(2,1,1)
            ax2=fig.add_subplot(2,1,2)
            zx=xxdata.mean(axis=0).mean(axis=1)
            zy=yydata.mean(axis=0).mean(axis=1)            
            ax1.plot(ants,zx,'b')
            ax1.plot(ants,zx,'b.')
            ax2.plot(ants,zy,'r')
            ax2.plot(ants,zy,'r.')
            ax2.set_xlabel('Antenna')
            ax1.set_ylabel('XX Amplitude')
            ax2.set_ylabel('YY Amplitude')
            ax1.xaxis.set_ticklabels('')
            ax1.set_title(title)
            fname='%s_antenna.%s' % (root,format)
            logger.info('# Saving amplitude vs. antenna to %s' % (fname))
            try:
                pylab.savefig(fname)
                outputfiles.append(fname)
            except RuntimeError,err:
                logger.error('Error saving figure: %s',err)                
            del ax1,ax2,ants

        if (level >= 2):
            time=1+numpy.arange(ntimes)
            yx=xxdata.mean(axis=2)
            minyx=numpy.repeat(numpy.reshape(yx.min(axis=0),(nants,1)),ntimes,axis=1)
            maxyx=numpy.repeat(numpy.reshape(yx.max(axis=0),(nants,1)),ntimes,axis=1)
            d=numpy.repeat(numpy.reshape(1+numpy.arange(nants),(nants,1)),ntimes,axis=1)
            zx=((yx.transpose()-minyx)/(maxyx-minyx)+d).transpose()
            yy=yydata.mean(axis=2)
            minyy=numpy.repeat(numpy.reshape(yy.min(axis=0),(nants,1)),ntimes,axis=1)
            maxyy=numpy.repeat(numpy.reshape(yy.max(axis=0),(nants,1)),ntimes,axis=1)
            zy=((yy.transpose()-minyy)/(maxyy-minyy)+d).transpose()
            # deal with entries that are all masked
            for antenna in xrange(nants):
                if (zx[:,antenna].mask.all()):
                    zx[:,antenna] *= 0
                    zx[:,antenna].mask=False
                if (zy[:,antenna].mask.all()):
                    zy[:,antenna] *= 0
                    zy[:,antenna].mask=False
            fig.clf()
            #fig=pylab.figure()
            ax=fig.add_subplot(1,1,1)
            lines=ax.plot(time,zx,'-',time,zy,'--')
            leg=ax.legend((lines[0],lines[nants]),('XX','YY'))
            ax.set_xlabel('Time (samples)')
            ax.set_ylabel('Normalized Amplitude/Antenna')
            ax.set_title(title)
            fname='%s_time_antenna.%s' % (root,format)
            logger.info('# Saving amplitude per antenna vs. time to %s' % fname)
            try:
                pylab.savefig(fname)
                outputfiles.append(fname)
            except RuntimeError,err:
                logger.error('Error saving figure: %s',err)                            
            del ax,time,yx,minyx,maxyx,yy,minyy,maxyy,d,zx,zy,lines,leg

            chans=1+numpy.arange(nchan)
            yx=xxdata.mean(axis=0)
            minyx=numpy.repeat(numpy.reshape(yx.min(axis=1),(nants,1)),nchan,axis=1)
            maxyx=numpy.repeat(numpy.reshape(yx.max(axis=1),(nants,1)),nchan,axis=1)
            d=numpy.repeat(numpy.reshape(1+numpy.arange(nants),(nants,1)),nchan,axis=1)
            zx=((yx-minyx)/(maxyx-minyx)+d).transpose()
            yy=yydata.mean(axis=0)
            minyy=numpy.repeat(numpy.reshape(yy.min(axis=1),(nants,1)),nchan,axis=1)
            maxyy=numpy.repeat(numpy.reshape(yy.max(axis=1),(nants,1)),nchan,axis=1)
            zy=((yy-minyy)/(maxyy-minyy)+d).transpose()
            # deal with entries that are all masked
            for antenna in xrange(nants):
                if (zx[:,antenna].mask.all()):
                    zx[:,antenna] *= 0
                    zx[:,antenna].mask=False
                if (zy[:,antenna].mask.all()):
                    zy[:,antenna] *= 0
                    zy[:,antenna].mask=False
            #fig=pylab.figure()
            fig.clf()
            ax=fig.add_subplot(1,1,1)
            lines=ax.plot(chans,zx,'-',chans,zy,'--')
            leg=ax.legend((lines[0],lines[nants]),('XX','YY'))
            ax.set_xlabel('Channel Number')
            ax.set_ylabel('Normalized Amplitude/Antenna')
            ax.set_title(title)
            fname='%s_channel_antenna.%s' % (root,format)
            logger.info('# Saving amplitude per antenna vs. channel to %s' % fname)
            try:
                pylab.savefig(fname)
                outputfiles.append(fname)
            except RuntimeError,err:
                    logger.error('Error saving figure: %s',err)                            
            del ax,chans,yx,minyx,maxyx,yy,minyy,maxyy,d,zx,zy,lines,leg

        if (level >= 3):
            for antenna in xrange(nants):
                #fig=pylab.figure()
                fig.clf()
                fig.subplots_adjust(hspace=-0.0)
                ax1=fig.add_subplot(2,1,1)
                ax2=fig.add_subplot(2,1,2)                
                dx=xxdata[:,antenna,:].data
                dy=yydata[:,antenna,:].data
                if (not xxdata[:,antenna,:].mask.all()):
                    dx[numpy.nonzero(xxdata[:,antenna,:].mask)]=pylab.nan
                if (not yydata[:,antenna,:].mask.all()):
                    dy[numpy.nonzero(yydata[:,antenna,:].mask)]=pylab.nan
                #i1=ax1.imshow(dx,cmap=pylab.cm.hsv,aspect='equal')
                #i2=ax2.imshow(dy,cmap=pylab.cm.hsv,aspect='equal')
                i1=ax1.imshow(dx.transpose(),cmap=pylab.cm.hsv,aspect='auto')
                i2=ax2.imshow(dy.transpose(),cmap=pylab.cm.hsv,aspect='auto')
                if (xxdata[:,antenna,:].mask.all()):
                    ax1.text(1,nchan/2,'FLAGGED')
                else:
                    dx[numpy.nonzero(xxdata[:,antenna,:].mask)]=pylab.nan
                if (yydata[:,antenna,:].mask.all()):
                    ax2.text(1,nchan/2,'FLAGGED')
                else:                    
                    dy[numpy.nonzero(yydata[:,antenna,:].mask)]=pylab.nan                    
                ax1.text(1,1,'XX Amplitude')
                ax2.text(1,1,'YY Amplitude')
                ax1.set_ylabel('Channel')
                ax2.set_ylabel('Channel')
                # make the axis direction normal
                ax1.invert_yaxis()
                ax2.invert_yaxis()
                ax1.xaxis.set_ticklabels('')
                ax1.set_title('%s: %d' % (title,antenna+1))
                ax2.set_xlabel('Time (samples)')
                fname='%s_image_%02d.%s' % (root,antenna+1,format)
                try:
                    
                    logger.info('# Saving waterfall plot for antenna %d to %s'
                                % (antenna+1,fname))
                    pylab.savefig(fname)
                    outputfiles.append(fname)
                except RuntimeError,err:
                    logger.error('Error saving figure: %s',err)                            

        return outputfiles
