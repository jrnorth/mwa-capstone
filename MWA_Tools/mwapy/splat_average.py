import sys,os,logging,shutil,datetime,re,subprocess,math,tempfile,string,glob
from optparse import OptionParser
import numpy

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('splat_average')
logger.setLevel(logging.WARNING)


# digital PFB gains, one per channel, used in the ADFBs
# from Ed Morgan, 2012-09-12
_PFB_gains=[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,3,3,3,3,3,3,3,3,3,3,3,3,3,4,4,4,4,4,4,4,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,6,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7]


######################################################################
def channel_order(center_channel):
    """
    correct_chan=channel_order(center_channel)
    gives the mapping between the input channels and the correct order
    depends on the center channel
    will return an array with length either to the number of coarse PFB channels
    """
    if (center_channel <= 12 or center_channel > 243):
        logger.error('Center channel must be between 13 and 243')
        return None
    correct_chan=numpy.zeros((24,),dtype=int)
    # Calculate the output channel order.
    minchan=center_channel-12
    nbank1=0
    nbank2=0
    for ii in xrange(minchan, minchan+24):
        if (ii<=128):
            nbank1+=1
        else:
            nbank2+=1
    for ii in xrange(nbank1):
        correct_chan[ii]=ii
    for ii in xrange(nbank2):
        correct_chan[ii+nbank1]=23-ii
    
    logger.info('Channel order: %s' % (','.join([str(x) for x in (minchan+correct_chan)])))
    return correct_chan
######################################################################
def get_gains(center_channel):
    """
    gains=get_gains(center_channel)
    returns the coarse PFB digital gains
    24 numbers, one per channel

    """
    if (center_channel <= 12 or center_channel > 243):
        logger.error('Center channel must be between 13 and 243')
        return None
    return _PFB_gains[center_channel-12:center_channel+12]


######################################################################
def get_filenames_integrations(root, ndas, chansperdas, inputs):
    """
    fnames_ac,fnames_cc,n_times=get_filenames_integrations(root, ndas, chansperdas, inputs)

    given a root, will search for <root>_das[1234].lacspc and <root>_das[1234].lccspc
    or with .LACSPC, .LCCSPC

    returns the names of the AC and CC files, along with the number of integrations

    will look for <ndas> files
    """
    acsize=[]
    n_times_ac=[]
    fin_cc=[]
    ccsize=[]
    n_times_cc=[]
    fnames_ac=[]
    fnames_cc=[]
    for k in xrange(ndas):
        if (ndas>1):
            fname_ac=root + ('_das%d.LACSPC' % (k+1))
            fname_cc=root + ('_das%d.LCCSPC' % (k+1))
            if (not os.path.exists(fname_ac)):
                fname_ac=root + ('_das%d.lacspc' % (k+1))
                fname_cc=root + ('_das%d.lccspc' % (k+1))
        else:
            fname_ac=root + ('.LACSPC')
            fname_cc=root + ('.LCCSPC')
            if (not os.path.exists(fname_ac)):
                fname_ac=root + ('.lacspc')
                fname_cc=root + ('.lccspc')
            

        fnames_ac.append(fname_ac)
        fnames_cc.append(fname_cc)
        # get file sizes
        try:
            acsize.append(os.path.getsize(fname_ac))
            logger.info("AC size for DAS %d: %d bytes" % (k+1,acsize[-1]))
        except:
            logger.error('Cannot find AC file for DAS %d' % (k+1))
            return None
        try:
            ccsize.append(os.path.getsize(fname_cc))
            logger.info("CC size for DAS %d: %d bytes" % (k+1,ccsize[-1]))
        except:
            logger.error('Cannot find CC file for DAS %d' % (k+1))
            return None
        n_times_ac.append(acsize[-1]/((chansperdas)*inputs*4))
        # CC needs two floats since data are complex
        n_times_cc.append(ccsize[-1]/(chansperdas*inputs*(inputs-1)/2*8))
        logger.info("Num integrations in AC for DAS %d: %d" % (k+1,n_times_ac[-1]))
        logger.info("Num integrations in CC for DAS %d: %d" % (k+1,n_times_cc[-1]))
        if (n_times_ac[k] != n_times_cc[k]):
            logger.error('AC integrations for DAS %d (%d) does not match CC integrations for DAS %d (%d)' % (
                    k+1,n_times_ac[k],k+1,n_times_cc[k]))
            return None
                       
        if (k>0):
            if n_times_ac[k] != n_times_ac[k-1]:
                logger.warning('AC integrations for DAS %d (%d) does not match that for DAS %d (%d)' % (
                    k+1,n_times_ac[k],k,n_times_ac[k-1]))

    return fnames_ac,fnames_cc,min(n_times_ac)
    
######################################################################
def splat_average_ac(innames, outname, ntimes, nchan, ninp, n_avtime, n_avfreq, correct_chan, quack=0, gains=None):
    """
    result=splat_average_ac(innames, outname, ntimes, nchan, ninp, n_avtime, n_avfreq, correct_chan, quack=0, gains=None)
    innames is a list of input AC filenames
    outname is the output file (or a list of output files)
    ntimes is the number of integrations
    nchan is the total number of channels (over all DASs)
    ninp is the number of correlator inputs (2*antennas)
    n_avtime is the number of integrations to average (>=1)
    n_avfreq is the number of channels to average (>=1)
    correct_chan is the mapping between input channel order and correct order
    will quack the first <quack> time samples (set them to 0)
    gains is a list/array of 24 numbers for the coarse PFB channels gains: the inverse of this is applied
    (if gains==None, nothing is done)
    

    if result is not None, success
    """

    if quack > 0:
        if int(quack) % int(n_avtime) > 0:
            # not an integer multiple
            logger.warning('Requested quacking time of %d is not a multiple of requested time averaging %d; increasing quacking to %d...' % (
                quack,n_avtime,((int(quack)/int(n_avtime))+1)*int(n_avtime)))
            quack=((int(quack)/int(n_avtime))+1)*int(n_avtime)
    
    fin_ac=[]
    ndas=len(innames)
    for k in xrange(ndas):
        try:
            fin_ac.append(open(innames[k],'rb'))
            logger.info('Opened AC file for DAS %d: %s' % (k+1,innames[k]))
        except:
            logger.error('Cannot open AC file for DAS %d: %s' % (k+1,innames[k]))
            return None
    subbands=1
    if (isinstance(outname,str) or len(outname)==1):
        try:
            if (os.path.exists(outname)):
                os.remove(outname)
            fout_ac=open(outname,'wb')
            logger.info('Writing AC output to %s' % outname)
        except:
            logger.error('Could not open AC file %s for writing' % outname)
            return None
    else:
        subbands=len(outname)
        fout_ac=[]
        for outn in outname:
            try:
                if (os.path.exists(outn)):
                    os.remove(outn)
                fout_ac.append(open(outn,'wb'))
                logger.info('Writing AC output to %s' % outn)
            except:
                logger.error('Could not open AC file %s for writing' % outn)
                return None
        
    indata=numpy.zeros((ninp,nchan),dtype=numpy.float32)
    outdata=numpy.zeros((ninp,nchan),dtype=numpy.float32)
    if (n_avtime>1):
        D=numpy.zeros((n_avtime,ninp,nchan),dtype=numpy.float32)
        shape=D.shape
    i=0
    chanperdas=nchan/ndas
    chanpercoarse=nchan/len(correct_chan)
    if n_avfreq>1:
        # construct an index array for block summing
        ind=numpy.empty((nchan/subbands/n_avfreq)*2,dtype=numpy.int32)
        ind[::2]=numpy.arange(0,nchan/subbands,n_avfreq)
        ind[1::2]=numpy.arange(n_avfreq,nchan/subbands+n_avfreq,n_avfreq)
        
    for t in xrange(ntimes):
        for k in xrange(ndas):
            try:
                indata[:,k*chanperdas:(k+1)*chanperdas]=numpy.fromfile(file=fin_ac[k],
                                                                       dtype=numpy.float32,
                                                                       count=chanperdas*ninp).reshape((ninp,chanperdas))
            except:
                indata[:,k*chanperdas:(k+1)*chanperdas]=0
                
        if t < quack:
            indata[:,:]=0

        for j in xrange(24):
            outdata[:,j*chanpercoarse:(j+1)*chanpercoarse]=indata[
                :,correct_chan[j]*chanpercoarse:(correct_chan[j]+1)*chanpercoarse]
            if gains is not None:
                outdata[:,j*chanpercoarse:(j+1)*chanpercoarse]/=float(gains[j])**2
        if n_avtime>1:
            D[i]=outdata
        else:
            if subbands==1:
                if n_avfreq>1:
                    (numpy.add.reduceat(outdata, ind[:-1], axis=1)[:,::2]/n_avfreq).tofile(fout_ac)
                else:
                    outdata.tofile(fout_ac)
            else:
                for subband in xrange(subbands):
                    if n_avfreq>1:
                        (numpy.add.reduceat(outdata[:,(nchan/subbands)*subband:(nchan/subbands)*(subband+1)],
                                            ind[:-1], axis=1)[:,::2]/n_avfreq).tofile(fout_ac[subband])       
                                            
                    else:
                        outdata[:,(nchan/subbands)*subband:(nchan/subbands)*(subband+1)].tofile(fout_ac[subband])                        
        if n_avtime>1:
            i+=1
            if (i>=n_avtime):
                Dav=D.mean(axis=0)
                if (subbands==1):
                    if n_avfreq>1:
                        (numpy.add.reduceat(Dav, ind[:-1], axis=1)[:,::2]/n_avfreq).tofile(fout_ac)
                    else:
                        Dav.tofile(fout_ac)
                else:
                    for subband in xrange(subbands):
                        if n_avfreq>1:
                            (numpy.add.reduceat(Dav[:,(nchan/subbands)*subband:(nchan/subbands)*(subband+1)],
                                                ind[:-1], axis=1)[:,::2]/n_avfreq).tofile(fout_ac[subband])  
                        else:
                            Dav[:,(nchan/subbands)*subband:(nchan/subbands)*(subband+1)].tofile(fout_ac[subband])

                i=0

    for k in xrange(ndas):
        fin_ac[k].close()

    if (subbands==1):
        fout_ac.close()
    else:
        for fout in fout_ac:
            fout.close()
    return True

######################################################################
def splat_average_cc(innames, outname, ntimes, nchan, ninp, n_avtime, n_avfreq, correct_chan, quack=0, gains=None):
    """
    result=splat_average_cc(innames, outname, ntimes, nchan, ninp, n_avtime, n_avfreq, correct_chan, quack=0, gains=None)
    innames is a list of input CC filenames
    outname is the output file (or a list of output files)
    ntimes is the number of integrations
    nchan is the total number of channels (over all DASs)
    ninp is the number of correlator inputs (2*antennas)
    n_avtime is the number of integrations to average (>=1)
    n_avfreq is the number of channels to average (>=1)
    correct_chan is the mapping between input channel order and correct order
    will quack the first <quack> time samples (set them to 0)
    gains is a list/array of 24 numbers for the coarse PFB channels gains: the inverse of this is applied
    (if gains==None, nothing is done)
    
    if result is not None, success
    """
    if quack > 0:
        if int(quack) % int(n_avtime) > 0:
            # not an integer multiple
            logger.warning('Requested quacking time of %d is not a multiple of requested time averaging %d; increasing quacking to %d...' % (
                quack,n_avtime,((int(quack)/int(n_avtime))+1)*int(n_avtime)))
            quack=((int(quack)/int(n_avtime))+1)*int(n_avtime)
    

    fin_cc=[]
    ndas=len(innames)
    for k in xrange(ndas):
        try:
            fin_cc.append(open(innames[k],'rb'))
            logger.info('Opened CC file for DAS %d: %s' % (k+1,innames[k]))
        except:
            logger.error('Cannot open CC file for DAS %d: %s' % (k+1,innames[k]))
            return None
    subbands=1
    if (isinstance(outname,str) or len(outname)==1):
        try:
            if (os.path.exists(outname)):
                os.remove(outname)
            fout_cc=open(outname,'wb')
            logger.info('Writing CC output to %s' % outname)
        except:
            logger.error('Could not open CC file %s for writing' % outname)
            return None
    else:
        subbands=len(outname)
        fout_cc=[]
        for outn in outname:
            try:
                if (os.path.exists(outn)):
                    os.remove(outn)
                fout_cc.append(open(outn,'wb'))
                logger.info('Writing CC output to %s' % outn)
            except:
                logger.error('Could not open CC file %s for writing' % outn)
                return None

    # two because they are complex
    indata=numpy.zeros((ninp*(ninp-1)/2,nchan*2,),dtype=numpy.float32)
    outdata=numpy.zeros((ninp*(ninp-1)/2,nchan*2,),dtype=numpy.float32)
    logger.debug('arrays allocated')
    if (n_avtime>1):
        D=numpy.zeros((n_avtime,ninp*(ninp-1)/2,nchan*2),dtype=numpy.float32)
        shape=D.shape
    i=0
    chanperdas=nchan/ndas
    chanpercoarse=nchan/len(correct_chan)
    if n_avfreq>1:
        # construct an index array for block summing
        ind=numpy.empty((nchan/subbands/n_avfreq)*2,dtype=numpy.int32)
        ind[::2]=numpy.arange(0,nchan/subbands,n_avfreq)
        ind[1::2]=numpy.arange(n_avfreq,nchan/subbands+n_avfreq,n_avfreq)
        Dreal=numpy.zeros((ninp*(ninp-1)/2,nchan/subbands/n_avfreq),dtype=numpy.float32)
        Dimag=numpy.zeros((ninp*(ninp-1)/2,nchan/subbands/n_avfreq),dtype=numpy.float32)        
        Dout=numpy.zeros((ninp*(ninp-1)/2,nchan*2/subbands/n_avfreq),dtype=numpy.float32)        
    for t in xrange(ntimes):
        for k in xrange(ndas):
            try:
                indata[:,k*chanperdas*2:(k+1)*chanperdas*2]=numpy.fromfile(file=fin_cc[k],
                                                                           dtype=numpy.float32,
                                                                           count=chanperdas*2*ninp*(ninp-1)/2).reshape((ninp*(ninp-1)/2,chanperdas*2))
            except:
                indata[:,k*chanperdas*2:(k+1)*chanperdas*2]=0

            logger.debug('Read t=%d, das=%d' % (t,k))
        if t < quack:
            indata[:,:]=0
        for j in xrange(24):
            outdata[:,j*chanpercoarse*2:(j+1)*chanpercoarse*2]=indata[
                :,correct_chan[j]*chanpercoarse*2:(correct_chan[j]+1)*chanpercoarse*2]
            logger.debug('Rearranging coarse channel %d' % j)
            if gains is not None:
                outdata[:,j*chanpercoarse*2:(j+1)*chanpercoarse*2]/=float(gains[j])**2
        if n_avtime>1:
            D[i]=outdata
        else:
            if subbands==1:
                if n_avfreq>1:
                    # have to separate the real and imag
                    Dreal=(numpy.add.reduceat(outdata[:,::2], ind[:-1], axis=1)[:,::2]/n_avfreq)
                    Dimag=(numpy.add.reduceat(outdata[:,1::2], ind[:-1], axis=1)[:,::2]/n_avfreq)
                    Dout[:,::2]=Dreal
                    Dout[:,1::2]=Dimag
                    Dout.tofile(fout_cc)
                else:
                    outdata.tofile(fout_cc)
            else:
                for subband in xrange(subbands):
                    if n_avfreq>1:
                        Dreal=(numpy.add.reduceat(outdata[:,(2*nchan/subbands)*subband:(2*nchan/subbands)*(subband+1):2],
                                                  ind[:-1], axis=1)[:,::2]/n_avfreq)
                        Dimag=(numpy.add.reduceat(outdata[:,(2*nchan/subbands)*subband+1:(2*nchan/subbands)*(subband+1):2],
                                                  ind[:-1], axis=1)[:,::2]/n_avfreq)
                        Dout[:,::2]=Dreal
                        Dout[:,1::2]=Dimag
                        Dout.tofile(fout_cc[subband])
                    else:
                        outdata[:,(2*nchan/subbands)*subband:(2*nchan/subbands)*(subband+1)].tofile(fout_cc[subband])
        logger.debug('Wrote t=%d' % t)
        if n_avtime>1:
            i+=1
            if (i>=n_avtime):
                Dav=D.mean(axis=0)
                if (subbands==1):
                    if n_avfreq>1:
                        Dreal=(numpy.add.reduceat(Dav[:,::2], ind[:-1], axis=1)[:,::2]/n_avfreq)
                        Dimag=(numpy.add.reduceat(Dav[:,1::2], ind[:-1], axis=1)[:,::2]/n_avfreq)
                        Dout[:,::2]=Dreal
                        Dout[:,1::2]=Dimag
                        Dout.tofile(fout_cc)
                    else:
                        Dav.tofile(fout_cc)
                else:
                    for subband in xrange(subbands):
                        if n_avfreq>1:
                            Dreal=(numpy.add.reduceat(Dav[:,(2*nchan/subbands)*subband:(2*nchan/subbands)*(subband+1):2],
                                                      ind[:-1], axis=1)[:,::2]/n_avfreq)
                            Dimag=(numpy.add.reduceat(Dav[:,(2*nchan/subbands)*subband+1:(2*nchan/subbands)*(subband+1):2],
                                                      ind[:-1], axis=1)[:,::2]/n_avfreq)
                            Dout[:,::2]=Dreal
                            Dout[:,1::2]=Dimag
                            Dout.tofile(fout_cc[subband])
                        else:
                            Dav[:,(2*nchan/subbands)*subband:(2*nchan/subbands)*(subband+1)].tofile(fout_ac[subband])
                    
                i=0
    for k in xrange(ndas):
        fin_cc[k].close()

    if subbands==1:
        fout_cc.close()
    else:
        for fout in fout_cc:
            fout.close()
        
    return True

######################################################################
def splat_average_ac_pipe(outname, nchan, ncoarse, ninp, n_avtime, n_avfreq, correct_chan, gains=None):
    """
    result=splat_average_ac_pipe(outname, nchan, ncoarse, ninp, n_avtime, n_avfreq, correct_chan, gains=None)

    if outname is None, outputs to stdout

    nchan is the total number of channels (over all DASs)
    ncoarse is the number of coarse channels
    ninp is the number of correlator inputs (2*antennas)
    n_avtime is the number of integrations to average (>=1)
    n_avfreq is the number of channels to average (>=1)
    correct_chan is the mapping between input channel order and correct order
    gains is a list/array of <ncoarse> numbers for the coarse PFB channels gains: the inverse of this is applied
    (if gains==None, nothing is done)

    returns number of samples processed

    """

    if correct_chan is not None:
        if not len(correct_chan) == ncoarse:
            logger.error('Number of coarse channels %d does not map length of channel mapping array %d' % (
                ncoarse, len(correct_chan)))
            return None
    else:
        correct_chan=numpy.arange(ncoarse)
    if gains is not None:
        if not len(gains) == ncoarse:
            logger.error('Number of coarse channels %d does not map length of gains array %d' % (
                ncoarse, len(gains)))
            return None
    
    if (isinstance(outname,str)):
        try:
            # do not need to do this
            #if (os.path.exists(outname)):
            #    os.remove(outname)
            fout_ac=open(outname,'wb')
            logger.info('Writing AC output to %s' % outname)
        except:
            logger.error('Could not open AC file %s for writing' % outname)
            return None
    else:
        fout_ac=sys.stdout
        
    indata=numpy.zeros((ninp,nchan),dtype=numpy.float32)
    outdata=numpy.zeros((ninp,nchan),dtype=numpy.float32)
    if (n_avtime>1):
        D=numpy.zeros((n_avtime,ninp,nchan),dtype=numpy.float32)
        shape=D.shape
    i=0
    chanpercoarse=nchan/len(correct_chan)
    if n_avfreq>1:
        # construct an index array for block summing
        ind=numpy.empty((nchan/n_avfreq)*2,dtype=numpy.int32)
        ind[::2]=numpy.arange(0,nchan,n_avfreq)
        ind[1::2]=numpy.arange(n_avfreq,nchan+n_avfreq,n_avfreq)

    nprocessed=0
    while True:
        try:
            indata=numpy.fromfile(file=sys.stdin,
                                  dtype=numpy.float32,
                                  count=nchan*ninp).reshape((ninp,nchan))
        except:
            break
            
        for j in xrange(ncoarse):
            outdata[:,j*chanpercoarse:(j+1)*chanpercoarse]=indata[
                :,correct_chan[j]*chanpercoarse:(correct_chan[j]+1)*chanpercoarse]
            if gains is not None:
                outdata[:,j*chanpercoarse:(j+1)*chanpercoarse]/=float(gains[j])**2
        if n_avtime>1:
            D[i]=outdata
        else:
            if n_avfreq>1:
                try:
                    (numpy.add.reduceat(outdata, ind[:-1], axis=1)[:,::2]/n_avfreq).tofile(fout_ac)
                except ValueError:
                    break
            else:
                try:
                    outdata.tofile(fout_ac)
                except ValueError:
                    break
        if n_avtime>1:
            i+=1
            if (i>=n_avtime):
                Dav=D.mean(axis=0)
                if n_avfreq>1:
                    try:
                        (numpy.add.reduceat(Dav, ind[:-1], axis=1)[:,::2]/n_avfreq).tofile(fout_ac)
                    except ValueError:
                        break
                else:
                    try:
                        Dav.tofile(fout_ac)
                    except ValueError:
                        break
                i=0

        nprocessed+=1

    if (isinstance(outname,str)):
        fout_ac.close()
    return nprocessed

######################################################################
def splat_average_cc_pipe(outname, nchan, ncoarse, ninp, n_avtime, n_avfreq, correct_chan, gains=None):
    """
    result=splat_average_cc_pipe(outname, nchan, ncoarse, ninp, n_avtime, n_avfreq, correct_chan, gains=None)

    if outname is None, outputs to stdout

    nchan is the total number of channels (over all DASs)
    ncoarse is the number of coarse channels
    ninp is the number of correlator inputs (2*antennas)
    n_avtime is the number of integrations to average (>=1)
    n_avfreq is the number of channels to average (>=1)
    correct_chan is the mapping between input channel order and correct order
    gains is a list/array of 24 numbers for the coarse PFB channels gains: the inverse of this is applied
    (if gains==None, nothing is done)

    returns number of samples processed

    """

    if correct_chan is not None:
        if not len(correct_chan) == ncoarse:
            logger.error('Number of coarse channels %d does not map length of channel mapping array %d' % (
                ncoarse, len(correct_chan)))
            return None
    else:
        correct_chan=numpy.arange(ncoarse)
    if gains is not None:
        if not len(gains) == ncoarse:
            logger.error('Number of coarse channels %d does not map length of gains array %d' % (
                ncoarse, len(gains)))
            return None
    
    if (isinstance(outname,str)):
        try:
            # do not need to do this
            #if (os.path.exists(outname)):
            #    os.remove(outname)
            fout_cc=open(outname,'wb')
            logger.info('Writing CC output to %s' % outname)
        except:
            logger.error('Could not open CC file %s for writing' % outname)
            return None
    else:
        fout_cc=sys.stdout


    # two because they are complex
    indata=numpy.zeros((ninp*(ninp-1)/2,nchan*2,),dtype=numpy.float32)
    outdata=numpy.zeros((ninp*(ninp-1)/2,nchan*2,),dtype=numpy.float32)
    if (n_avtime>1):
        D=numpy.zeros((n_avtime,ninp*(ninp-1)/2,nchan*2),dtype=numpy.float32)
        shape=D.shape
    i=0
    chanpercoarse=nchan/len(correct_chan)
    if n_avfreq>1:
        # construct an index array for block summing
        ind=numpy.empty((nchan/n_avfreq)*2,dtype=numpy.int32)
        ind[::2]=numpy.arange(0,nchan,n_avfreq)
        ind[1::2]=numpy.arange(n_avfreq,nchan+n_avfreq,n_avfreq)
        Dreal=numpy.zeros((ninp*(ninp-1)/2,nchan/n_avfreq),dtype=numpy.float32)
        Dimag=numpy.zeros((ninp*(ninp-1)/2,nchan/n_avfreq),dtype=numpy.float32)        
        Dout=numpy.zeros((ninp*(ninp-1)/2,nchan*2/n_avfreq),dtype=numpy.float32)        
    nprocessed=0
    while True:
        try:
            indata=numpy.fromfile(file=sys.stdin,
                                  dtype=numpy.float32,
                                  count=nchan*2*ninp*(ninp-1)/2).reshape((ninp*(ninp-1)/2,nchan*2))
        except:
            break
            
        for j in xrange(ncoarse):
            outdata[:,j*chanpercoarse*2:(j+1)*chanpercoarse*2]=indata[
                :,correct_chan[j]*chanpercoarse*2:(correct_chan[j]+1)*chanpercoarse*2]
            if gains is not None:
                outdata[:,j*chanpercoarse*2:(j+1)*chanpercoarse*2]/=float(gains[j])**2
        if n_avtime>1:
            D[i]=outdata
        else:
            if n_avfreq>1:
                # have to separate the real and imag
                Dreal=(numpy.add.reduceat(outdata[:,::2], ind[:-1], axis=1)[:,::2]/n_avfreq)
                Dimag=(numpy.add.reduceat(outdata[:,1::2], ind[:-1], axis=1)[:,::2]/n_avfreq)
                Dout[:,::2]=Dreal
                Dout[:,1::2]=Dimag
                try:
                    Dout.tofile(fout_cc)
                except ValueError:
                    break
            else:
                try:
                    outdata.tofile(fout_cc)
                except ValueError:
                    break                

        if n_avtime>1:
            i+=1
            if (i>=n_avtime):
                Dav=D.mean(axis=0)
                if n_avfreq>1:
                    Dreal=(numpy.add.reduceat(Dav[:,::2], ind[:-1], axis=1)[:,::2]/n_avfreq)
                    Dimag=(numpy.add.reduceat(Dav[:,1::2], ind[:-1], axis=1)[:,::2]/n_avfreq)
                    Dout[:,::2]=Dreal
                    Dout[:,1::2]=Dimag
                    try:
                        Dout.tofile(fout_cc)
                    except ValueError:
                        break

                else:
                    try:
                        Dav.tofile(fout_cc)
                    except ValueError:
                        break

                    
                i=0
        nprocessed+=1
        

    if (isinstance(outname,str)):
        fout_cc.close()
    return nprocessed
