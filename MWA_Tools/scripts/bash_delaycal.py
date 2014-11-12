from time import time
import numpy as n
import aipy as a
import sys,os,optparse
import re
t0 = time()

import mwapy
import mwapy.get_observation_info
from mwapy.obssched.base import schedule

db=schedule.getdb()

####################################
##     Parse inputs               ##
####################################
o = optparse.OptionParser()
o.set_usage('bash_delaycal.py [options] *.ms')
o.set_description(__doc__)
#a.scripting.add_standard_options(o,cal=True,src=True)
o.add_option('-C','--cal',default='mwa_32T_pb',type=str,
    help="Which aipy cal file to use - defines the primary beam response. Default=mwa_32T_pb.")
o.add_option('-s','--src',default='all',type=str,
    help="Which sources to use, e.g. 'pic', if you want to use a particular source rather than the brightest. Default=all")
o.add_option('--cat',default='culgoora_150MHz',type=str,
    help="Which sky catalogue to use (located in <MWA_Tools install directory>/lib/python2.7/site-packages/mwapy/catalog . Default=culgoora_150MHz")
o.add_option('--fconfig',default='80_300_5',
    help='Start_stop_step for output image and cal in MHz.[80_300_5]')
o.add_option('--useflagversion',default=None,type='str',
    help='Version of flags to use [None]')
o.add_option('--minsnr',default=3,type='float',
    help='SNR threshold for calibration solution (see minsnr in CASA bandpass)')
o.add_option('--nsrcs',type='int',default=1,
    help="""Number of sources to include. Proxy for flux cut, but that depends where you are looking in the sky. You
    could do this in the srcs option, but that takes thinking. Default=5""")
o.add_option('--fov',type='float',default=90,
    help="""Radius in degrees to search for calibrator sources. Default = 90 """)
o.add_option('--antenna',type='str',default='',
    help="""Antenna string. See selection criteria in casa user manual. default = '' """)
o.add_option('--refant',default='',type=str,
    help="Reference antenna for phase cal")
o.add_option('--minsrc',type='int',default=None,
    help="""Minimum number of sources to include, if testing over a range. Inactive if nsrcs is specfied. Default=1""")
o.add_option('--maxsrc',type='int',default=None,
    help="""Minimum number of sources to include, if testing over a range. Inactive if nsrcs is specfied. Default=5""")
o.add_option('--caldir',type='string',default=None,
    help="""Destination for exported calibration solutions; if not selected, no export is performed""")
o.add_option("--overwrite", action="store_true", dest="overwrite",
    help="""Overwrite existing calibrations with new ones""")
o.add_option('--docal',action='store_true', dest="docal",
    help="""Generate the calibration solutions from CASA's bandpass routine""")
o.add_option('--dofit',action='store_true', dest="dofit",
    help="""Fit linear delays to the bandpass solutions (requires high SNR)""")
o.add_option('--apply_cal',action='store_true', dest="apply_cal",
    help="""Apply the calibration solutions""")
o.add_option('--apply_fit',action='store_true', dest="apply_fit",
    help='Actually apply the fitted bandpass. By default, just calculates the delays implied by the solution')
o.add_option('--doimage',action='store_true', dest="doimage",
    help="""Generate sample images of the calibrated data.""")
o.add_option('--practice',action='store_true', dest="practice",
    help="""Only calculate the sources you would use, generate the cl and cl image files, and quit.""")
#o.add_option('--suffix',dest='suffix',default='',
#    help="""Use this to tag multiple experiments done on a single file. [default=None].""")
#o.add_option('--fcat',default='misc',
#    help="Flux calibrator catalog.")
#o.add_option('--scratch',default=None,type='str',
#    help='Directory to use as scratch for imaging. Use to avoid NFS lock errors. Default=None')
#clean off the casa args:
for i in range(len(sys.argv)):
    if sys.argv[i]==inspect.getfile( inspect.currentframe()):break
opts, args = o.parse_args(sys.argv[i+1:])

########################
# parse options        #
########################

n.set_printoptions(suppress=True)

# Fix this.... at the moment they are already set so it gets confused
try:
    fconfig = n.array(opts.fconfig.split('_')).astype(n.float)
    fstart  =   fconfig[0]#120
    fstop   =   fconfig[1]#180
    df      =   fconfig[2]#1
except:
    print 'Fconfig badly set, format is --fconfig=FSTART_FSTOP_FSTEP'
    sys.exit(1)

skymodelcatalogs = opts.cat.split(',')#['misc','three_cr']#['culgoora_160']
ants = opts.antenna

try: aipycalfile = opts.cal
except: aipycalfile = mwa_32T_pb

if opts.minsrc is not None :
    minsrc=opts.minsrc
    if opts.maxsrc is not None :
        maxsrc=opts.maxsrc
    else :
        print 'Maximum number of sources to test not set!'
else :
    minsrc=maxsrc=opts.nsrcs

##########################
# a few cheeky hardcodes #
##########################

pols=['XX','YY']
solint='10min'
uvrange='>20lambda'
mincalsnr=2
maxcalflag=0.66

flush = sys.stdout.flush

########################
# function definitions #
########################

def aipysrc2dir(aipysrc):
    P = aipysrc.get_params('*')
    ra,dec = P['ra'],P['dec']
    return me.direction('J2000','%5.6frad'%(ra,),'%5.6frad'%(dec,))

def dir2strlist(d):
    return qa.formxxx(me.getvalue(me.measure(d,'s'))['m0'],format='hms')+' '+qa.formxxx(me.getvalue(me.measure(d,'s'))['m1'],format='dms')

def is_src(src,jd,aa):
    return True

def beam(aipysrc,aipycalfile,jd,freq):
    return A
def pjys(src,aa,pol='XX'):
    src.compute(aa)
    if pol=='XX':
	bm = aa[0].bm_response(src.get_crds('top'))
    else:
	bm = aa[1].bm_response(src.get_crds('top'))
    return src.jys*bm
def MJDs2JD(t):
    return t/86400 + 2400000.5
def findcalsrcs(aa,cat,Nsrcs=1,altmin=10):
#    ia.open(imagename)
    cat.compute(aa)
    visible_cat = {}
    for src in cat:
#	 if srcinimage(ia,cat[src]): visible_cat[src] = cat[src]
	if cat[src].alt>(altmin*n.pi/180):visible_cat[src] = cat[src]
    sorted_cat = sorted(visible_cat.iteritems(),key=lambda src: pjys(src[1],aa),reverse=True)
#    ia.close()
#    return ([(src[0],pjys(src[1],aa),src[1].ra,src[1].dec,src[1].alt,src[1].index,src[1].mfreq) for src in sorted_cat[:Nsrcs]],
#	 [dir2strlist(aipysrc2dir(src[1])) for src in sorted_cat[:Nsrcs]])
    return [src[0] for src in sorted_cat[:Nsrcs]]
def dB(A):
    return 10*n.log10(A)

def get_aa(cal_key,freqs,bm_delays=None):
    exec('from %s import get_aa as _get_aa' % cal_key)
    return _get_aa(freqs,bm_delays)

#def use_src(cat,Nsrcs=1):
#    visible_cat = {}
#    for src in cat:
#	 if is_src(): visible_cat[src] = cat[src]
#    sorted_cat = sorted(visible_cat.iteritems(),key=lambda src: units.pjys(src[1],aa),reverse=True)
#    return ([(src[0],units.pjys(src[1],aa),src[1].ra,src[1].dec,src[1].alt,src[1].index,src[1].mfreq for src in sorted_cat[:Nsrcs]],[dir2strlist(aipysrc2dir(src[1])) for src in sorted_cat[:Nsrcs]])])

#def how_far(ra1,dec1,ra2,dec2):
#    lambda_diff = ra1 - ra2
#    num = (np.cos(dec2)*np.sin(lambda_diff))**2. + (np.cos(dec1)*np.sin(dec2)-np.sin(dec1)*np.cos(dec2)*np.cos(lambda_diff))**2.
#    denom = np.sin(dec1)*np.sin(dec2) + np.cos(dec1)*np.cos(dec2)*np.cos(lambda_diff)
#    return np.arctan2(np.sqrt(num),denom)*(180./3.1415)

###########################
# start running the files #
###########################

for msfile in args:

# Create an empty record array for the stats from the calibration solutions
    calstats=n.recarray(((maxsrc-minsrc+1),),dtype=[('nsrcs', int), ('SNR', float), ('flagged', float)]) 

    if not os.path.exists(msfile):
        print msfile+' does not exist!'
        break
        break
# If file is a uvfits file, import it
    if os.path.splitext(msfile)[1]=='.uvfits' :
        newname=os.path.splitext(msfile)[0]+'.ms'
        rmtables(newname)
        importuvfits(fitsfile=msfile,vis=newname)
        msfile=newname
    vis=msfile
    root=os.path.splitext(msfile)[0]

    #################################
    # Get the frequency information #
    #################################
    
    ms.open(msfile)
    rec = ms.getdata(['axis_info'])
    df,f0 = (rec['axis_info']['freq_axis']['resolution'][len(rec['axis_info']['freq_axis']['resolution'])/2],rec['axis_info']['freq_axis']['chan_freq'][len(rec['axis_info']['freq_axis']['resolution'])/2])
    F =rec['axis_info']['freq_axis']['chan_freq'].squeeze()/1e6
    print "step: df [kHz], central frequency f0 [MHz]"
    print df/1.e3,f0/1.e6
    	
    ms.close()
    
    # Get the delays from the database
    # If it's a new-style obervation in GPS seconds, just use the number

# Get observation number directly from the measurement set
    tb.open(msfile+'/OBSERVATION')
    try:
        obsnum=int(tb.getcol('MWA_GPS_TIME'))
    except:
        # 128T ms doesn't seem to have "MWA_GPS_TIME" column... 
        # assume msfile is <obsnum>.ms
        obsnum = int(msfile[:-3])
    tb.close()

    info=mwapy.get_observation_info.MWA_Observation(obsnum,db=db)
    bm_delays=info.delays

    #########################################
    # Load the antenna array and beam model #
    #########################################
    
    if not bm_delays is None:
    #	    bm_delays = n.array(map(float,opts.bm_delays.split(',')))
        aa = get_aa(aipycalfile,n.array(f0/1.e9),bm_delays=bm_delays)
    else:
        aa = a.cal.get_aa(aipycalfile,n.array([f0/1.e9]))

    ################################
    # Test over a range of sources #
    ################################
    k=0
    for nsrcs in range(minsrc,maxsrc+1):
    	######################
    	# naming conventions #
    	######################

        suffix='_'+str(nsrcs)    	
    	cl_name = msfile[:-3]+suffix+'.cl'
    	cal_name = msfile[:-3]+suffix+'.cal'

        clearcal(msfile)
 
    	srclist,coff,catalogs = a.scripting.parse_srcs(opts.src, opts.cat)
    	print aipycalfile,srclist,coff,catalogs
    	cat = a.cal.get_catalog(aipycalfile,srclist,coff, catalogs)
    	cat.compute(aa)
    	try:
    	    assert(len(cat)>0)
    	except:
    	    print "ERROR: No sources found. Is your catalog file in the PYTHONPATH?"
    	    raise

    	#find the median time
    	ms.open(msfile)
    	rec = ms.getdata(['time'])
    	t = n.median(rec['time'])
    	print "median time: MJD [s], JD [d]"
    	print t,MJDs2JD(t)
    	aa.set_jultime(MJDs2JD(t))
    	print "reading in the flags of input dataset"
    	frec = ms.getdata(['flag'])
    	FLAGS = frec['flag'].squeeze()
     
    	ms.close()
    
    	use_src = ['pic']#,'144']
    	print "Choosing a cal source(s)"
    	use_src = findcalsrcs(aa,cat,Nsrcs=nsrcs,altmin=(90-opts.fov))
    	print "Using",','.join(use_src)
    	 
    	#Make component list
    	#cl.open()
    	for src in use_src:
    	    s = cat[src]
    	#    f = s._jys*(0.16/s.mfreq)**s.index
    	    f_xx = pjys(cat[src],aa,pol='XX').squeeze()
    	    f_yy = pjys(cat[src],aa,pol='YY').squeeze()
    	    flux = n.array([f_xx,f_yy,0,0]).squeeze()
    	    w = 5.*(150./160.)
    	    print '='*50
    	    print 'Using src:',src
    	    print 'RA, dec =',s.ra,s.dec
    	    print 'flux (XX,YY,XY,YX)[pJys] =',flux
    	    print 'beam (A_X^2, A_Y^2) = ',flux/s.jys
    	    flux = n.array([((f_xx+f_yy)/2.0),((f_xx-f_yy)/2.0),0,0]).squeeze()
    	    print 'flux (I,Q,U,V)[pJys] =',flux
    	    print 'index =',s.index
    	    print 'width =',w,'arcmin'
    	    print '='*50
    	    flush()
    	    try: ind = s.index[0]
    	    except(TypeError,IndexError): ind = s.index
    	    cl.addcomponent(dir = aipysrc2dir(cat[src]),
# Finding that Gaussians really mess up the longer baseline arrays
    			    shape = 'point',
#    			    shape = 'Gaussian',
#    			    majoraxis = '%2.0farcmin'%w,
#    			    minoraxis = '%2.0farcmin'%w,
#    			    positionangle = '0deg',
    	#		     flux = [f,0.,0.,0.],
    			    flux = flux,
    #			     polarization='linear', #Functionality currently broken in CASA
    			    polarization='Stokes', #assumes standard bore-center conversion from stokes to linear
    			    freq = qa.quantity(f0,'Hz'),
    			    spectrumtype = 'spectral index',
    			    index = ind,
    			    label = src )
    	if os.path.exists(cl_name):
    	    print "overwriting %s"%cl_name;flush()
    	    os.system('rm -rf %s'%cl_name)
    	cl.rename(cl_name)
    	cl.close()
       
    	################################
    	#   Make an image of the model #
    	################################
    	ms.open(msfile)
    	modelimage = cl_name+'.im'
    	print "See %s for model image"%(modelimage)
    	cl.done()
    	cl.open(cl_name)
    	ia.fromshape(modelimage,[2000,2000,1,1],overwrite=True)
    	ia.setrestoringbeam(major='3arcmin',minor='3arcmin',pa='0deg')
    	cs=ia.coordsys()
    	cs.setunits(['rad','rad','','Hz'])
    	cell_rad=qa.convert(qa.quantity("3arcmin"),"rad")['value']
    	cs.setincrement([-cell_rad,cell_rad],'direction')
        if 'header' in ms.summary().keys():
            cs.setreferencevalue([qa.convert(ms.summary()['header']['field_0']['direction']['m0']['value'],ms.summary()['header']['field_0']['direction']['m0']['unit'])['value'],qa.convert(ms.summary()['header']['field_0']['direction']['m1']['value'],ms.summary()['header']['field_0']['direction']['m1']['unit'])['value']],type='direction')
        else:  # CASA 4.0 and onwards
            cs.setreferencevalue([qa.convert(ms.summary()['field_0']['direction']['m0']['value'],ms.summary()['field_0']['direction']['m0']['unit'])['value'],qa.convert(ms.summary()['field_0']['direction']['m1']['value'],ms.summary()['field_0']['direction']['m1']['unit'])['value']],type='direction')
    	cs.setreferencevalue('%fMHz'%(f0/1e6),'spectral')
    	cs.setincrement('%fkHz'%(df/1e3),'spectral')
    	ia.setcoordsys(cs.torecord())
    	ia.setbrightnessunit("Jy/beam")
    	#ia.modify(cl.torecord(),subtract=False)
        for i in range(cl.length()):
	    print "adding component ",cl.getcomponent(i)['label']
	    sys.stdout.flush()
	    ia.modify({'component0':cl.getcomponent(i),'nelements':1},subtract=False)
    	exportfits(imagename=modelimage,fitsimage=modelimage[:-3]+'.fits',overwrite=True)
    	print "and ",modelimage[:-3]+'.fits'
    	ms.close()
    	print "done"
      	cl.close()
        if opts.practice: continue
    	################################
    	#print "clearcal";flush()
    	#clearcal()
    	#Make the model
    	if not opts.useflagversion is None: 
            print "restore known good flags";flush()
            flagmanager(vis=vis,mode='restore',versionname=opts.useflagversion)
    	
    	
    	print 'Make a Model';flush()
    	spw = '0:%d~%dMHz'%(fstart,fstop)
    	
    	ft(vis=msfile,
    	    spw=spw,
    	    complist=cl_name,
    	    incremental=False)
    	
    	print '='*50
    	pl.figure(10)
    	pl.clf()
    	pl.figure(11)
    	if opts.docal:
    	    print 'GAINCAL'
    	    flush()
    	    bandpass(vis=msfile,
    		    caltable=cal_name,
    		    spw=spw,
    		    refant=opts.refant,
    		    selectdata=True,
    		    timerange='',
    		    scan='',
    		    uvrange=uvrange,
    		    antenna=ants,
    		    solint=solint,
    	#	     gaintype='G',
    		    bandtype='B',
    	#	     calmode='ap',
    		    interp=['nearest'],
    		    fillgaps=0,
    		    solnorm=False,
    		    minsnr=opts.minsnr)
    	    print '='*50
    	    tb.open(cal_name,nomodify=False)
    	    try: G = tb.getcol('GAIN')
    	    except: G = tb.getcol('CPARAM')

    	    M = tb.getcol('FLAG')
    	    SNR = n.ma.array(tb.getcol('SNR').squeeze(),mask=M.squeeze())
    	    print "="*100
    	    print "The SNR averaged to : %5.1f"%SNR.mean()
    	    print "Percent of data flagged at the beginning: %5.1f"%((n.mean(FLAGS))*100)
    	    print "Percent flagged in PASSBAND solutions: %5.1f"%(n.mean(M) *100)
    	    #print "Percent new data flagged [attempted calculation]: %5.1f"%(n.ma.array(M,mask=FLAGS).mean()*100)
    	    print "="*100
    	    calstats['nsrcs'][k]=nsrcs
            calstats['SNR'][k]=SNR.mean()
    	    calstats['flagged'][k]=n.mean(M)
            k+=1
    	    n.savez(cal_name,G=G,freq=F,mask=M.squeeze(),SNR=SNR.filled(-1))
            lines = []

            if opts.dofit:
    	    #for each spectrum compute a linear delay model
    	    #then replace the existing channelwise model with the delay model
       	        dlylog = open(cal_name+'.txt','w')
  	        for i in range(G.shape[2]):
    		    P,res,rank,sv,cond = n.ma.polyfit(n.ma.array(F/1e3),n.ma.array(n.unwrap(n.angle(G[0,:,i]),discont=2.6),mask=M[0,:,i]),1,full=True)
    		    AP,Ares,Arank,Asv,Acond = n.ma.polyfit(F/1e3,n.ma.array(n.abs(G[0,:,i]),mask=M[0,:,i]),2,full=True)
    		    ampmodel = n.poly1d(AP)
    		    if rank<2: P,res = [0,0],n.array([0.0])
    #		 print len(P),P[1],res.squeeze(),rank,cond,sv
    		    print "Ant: %d,\t Delay [ns]: %3.2f,\t Phase res [r]: %3.2f, \t Amp [Jys/count] %3.2f"%\
    		    (i,P[1]/(2*n.pi),res.squeeze()/(G.shape[1]-rank),ampmodel(.150));flush()
    		    pl.figure(10)
    		    l = pl.plot(F,n.ma.masked_where(M[0,:,i],n.unwrap(n.angle(G[0,:,i]),discont=2.6)),label=str(i))[0]
    		    pl.figure(11)
    		    pl.plot(F,n.ma.masked_where(M[0,:,i],dB(n.abs(G[0,:,i]/n.abs(G[0,:,i]).max()))),label=str(i),color=l.get_color())
    		    pl.plot(F,n.ma.masked_where(M[0,:,i],dB(ampmodel(F/1e3)/n.abs(G[0,:,i]).max())),color=l.get_color())
    		    lines.append(l)
    		    phasemodel = n.poly1d(P)
    		    pl.figure(10)
    		    pl.plot(F,phasemodel(F/1e3),color=l.get_color())
    		    if opts.apply_cal and opts.apply_fit:
    #		     G[0,:,i] = n.abs(G[0,:,i])*n.exp(1j*phasemodel(F/1e3))
    		        G[0,:,i] = ampmodel(F/1e3)*n.exp(1j*phasemodel(F/1e3))
    		    dlylog.write('%d \t'%i)#output the index
    		    for p in P:
    		        dlylog.write('%3.2f\t'%p)
    		    dlylog.write('%3.2f\t'%(res.squeeze()/(G.shape[1]-rank)))
    		    dlylog.write('\n')
    	        dlylog.close()
    	#pl.legend(numpoints=1,mode='expand',ncol=8)
    	        for fi in [10,11]:
    	            pl.figure(fi)
    	            ax = pl.gca()
    	            pl.figlegend(lines,map(str,range(G.shape[2])),'top center',numpoints=1,mode='expand',ncol=8)
    	            pl.xlabel('Freq [MHz]')
    	            pl.figure(10)
    	            pl.ylabel('gain phase [r]')
    	            pl.savefig(msfile+suffix+'.delaymodel.png')
    	            pl.figure(11)
    	            pl.ylabel('gain [dB]')
    	            pl.savefig(msfile+suffix+'.ampmodel.png')

###########################
## Pick the best solution##
###########################
# Basic check to see if the array got filled
    if calstats['nsrcs'][0]:
     # Sorts by % flagged
       sorted_stats=n.sort(calstats, order='flagged')  # toggle this for reverse: [::-1]
     # Get SNR and nsrcs for least-flagged solution
       srcval=sorted_stats['nsrcs'][0:1][0]
       snrval=sorted_stats['SNR'][0:1][0]
       flagval=sorted_stats['flagged'][0:1][0]
       print 'The best calibration was produced using %d source(s)'%srcval
       cwd=os.getcwd()+'/'
       calname=cwd+root+'_'+str(srcval)+'.cal'
       if snrval>=mincalsnr and flagval<=maxcalflag:
          print 'Flagging %5.1fpercent< maximum value (%5.1fpercent)'%(flagval*100,maxcalflag*100)
          print 'S/N %2.1f > minimum value (%2.1f)'%(snrval,mincalsnr)
# If you want to, export the best calibration solution
          if opts.caldir is not None:
             caldir=opts.caldir
             npzname=calname+'.npz'
             caltemp=cwd+root+'.cal'
             npztemp=caltemp+'.npz'
             caldest=caldir+'/'+root+'.cal'
             npzdest=caldest+'.npz'
             print 'Copying %s%s_%d.cal.npz to %s'%(cwd,root,srcval,caldir)
             if opts.overwrite is True:
                if os.path.exists(npzdest):
                    os.remove(npzdest)
                if os.path.exists(npztemp):
                    os.remove(npztemp)
                if os.path.exists(caldest):
                    shutil.rmtree(caldest)
                if os.path.exists(caltemp):
                    shutil.rmtree(caltemp)
    # Copy numpy arrays
             os.rename(npzname,npztemp)
             shutil.copy(npztemp,caldir)
             os.rename(npztemp,npzname)
    # Copy CASA tables
             os.rename(calname,caltemp)
             shutil.copytree(caltemp,caldest)
             os.rename(caltemp,calname)
       else:
          print 'Flagging %5.1f percent > maximum value (%5.1f percent) OR'%(flagval*100,maxcalflag*100)
          print 'S/N %2.1f < minimum value (%2.1f)'%(snrval,mincalsnr)
          print 'The best calibration did not meet the specified requirements.'
# Apply the best calibration, regardless of whether it meets the export requirements
# (Poor calibration is a more useful diagnostic than no calibration)
       if opts.apply_cal:
          try: tb.putcol('GAIN',G)
          except: tb.putcol('CPARAM',G)
          tb.close()
    	  print 'Running applycal using %s'%calname
    	  flush()
    	  applycal(vis=msfile,spw=spw,gaintable=calname)
       print '='*50
       print "store the SNR flag table"
       flagmanager(vis=vis,mode='save',versionname='delaycal')
       print 'Computation time: %2.1f m'%((time()-t0)/60.,)
       print '='*50

       if opts.doimage:
          if not opts.apply_cal:
             print 'Calibration not applied! Image will be broken unless calibration was previously applied by another process!'
          for stokes in pols:
    	     im=root+'_'+str(srcval)+'_'+stokes
             print 'Imaging data: %s'%im
             rmtables(im+'*')
    	     clean(vis=msfile, imagename=im, gridmode='widefield', psfmode='hogbom', imagermode='csclean', wprojplanes=1, facets=1, niter=5000, imsize=[2048, 2048], cell=['1arcmin', '1arcmin'], threshold='1.0Jy', stokes=stokes, mode='mfs', selectdata=True, uvrange='0.01~3klambda', weighting='uniform')
    	     beam=root+'_'+stokes+'.beam'
             imagename=im+'.image'
    	     if not os.path.exists(beam): 
    	          pbgain(imagename=imagename,pbimage=beam,delays=bm_delays)
    	     pbcor=im+'.pbcor'
    	     impbcor(imagename=imagename,pbimage=beam,outfile=pbcor,cutoff=0.1)
             exportfits(pbcor,pbcor[:-6]+'.fits',overwrite=True)
             exportfits(imagename,imagename[:-6]+'.fits',overwrite=True)
    else: print '%s did not produce useable calibrations'%(root)


