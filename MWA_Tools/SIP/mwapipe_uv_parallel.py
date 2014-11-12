import numpy
import os,os.path,sys
import math
from datetime import datetime, date, time, timedelta
import logging
import shutil
from threading import current_thread
import traceback
import tempfile
import time
import re
import pyfits
import csv

from mwapy import fits_utils as FU
from mwapy.pb import mwapb

import mwapy
import mwapy.get_observation_info
from mwapy.obssched.base import schedule
from mwapy.match_observation import *
db=schedule.getdb()

###########################################

# mwapipe_uv.py based on C. Williams CASA pipeline and D. Kalpans MIRIAD pipeline.
# This script will reduce uvfits files generated from raw MWA correlator L-files.
# This scripts starts from the uvfits stage so you the user will have to generate the uvfits 
# seperately. All the parameters to run the pipeline are set in parset.txt. The location of 
# the parset.txt file must be set below. This script works with CASA 3.3.0 and it also requires 
# pyfits to be installed. See README for installation instructions.
# This pipeline will produce a fits image (+beam image if dopbcor = True) for XX, YY and I for
# the full bandwidth available, and also as many subbands that are defined by nfreq and dosub = True 
# (see parset.txt). Each image is stored as an extra extension in the fits image. 
# The images are also combined so that they are readable by the transients detection pipeline.

# TODOs:
# 1.) Improve autoflagging for different expeditions
# 2.) Replace calls to flagdata with calls to tflagdata (NHW: Done 30/10/2012)
# 3.) Selfcal - do we need it
# 4.) Add support for database calls to generate delay files.  
# 5.) + more

############################################
##### Configuration-dependent path ########
# The pipeline must know where your parset file lives. 

#parset_file    = '/media/data/MWA/SIPTEST2/parset.txt'
parset_file = '/data2/MWA/alpha/EoR/parset.txt'

############################################
######## Get parameter set file ###########

def read_config():
    print 'Reading parameter set file'
    f = open(parset_file,'r')
    config_dict = {}
    for line in f:
        if line[0] == '#':
            pass;
        else:
            items = line.split('=', 1)
            config_dict[items[0]] = eval(items[1])
    return config_dict

##############################################

params = read_config()
OBSLIST = params['OBSLIST']
UVFITS_Scratch = params['UVFITS_Scratch']
results_dir = params['results_dir']
#delays_file = params['delays_file']

##############################################

def autoreduce(obsid, expedition, dosub, doimage, dopbcor, working_dir,out_dir):
    '''
    Task to reduce a given uvfits file using the settings defined in parset.txt.
    '''
    print 'Starting autoreduce (function:autoreduce)'
    vis = str(obsid)+'.ms'

    print "looking for %s"%vis
    if not os.path.exists(vis):
        print 'ms not found'
        print 'Importing UVFITS'
        fitsfile = str(obsid)+'.uvfits'
        importuvfits(fitsfile=fitsfile,vis=vis)
    get_field_name = vishead(vis=vis, mode='get', hdkey='source_name')
    field_name = (get_field_name[0])[0]
    print 'Observation ID = '+field_name 
    #print 'Running Flagging'
    #autoflag(vis,expedition=expedition)
    status = autocal(vis)
    if status:
        print "calibration failed"
        return 1
    print "Calibration finished (function:autoreduce)"
    ################################
    # Final flagging after calibration
    print 'Doing post calibration flagging with CASA autoflagger (function:autoreduce)'
    testautoflag(vis=vis, ntime=10, extendflags=false,timecutoff=4.0, freqcutoff=3.0, usepreflags=true, datacolumn='corrected', writeflags=True)
    print "Flagging finished, splitting data (function:autoreduce)."
    #### Split the data into frequency bins ###
    if dosub:
        params = read_config()
        nfreqs = params['nfreqs']
        freqbin=768/nfreqs
        splitvises=[]
        visroot = os.getcwd()
        for chan in range(nfreqs):
            newvis=visroot+'/f'+`chan`+'.ms'
            spw='0:%i~%i'%(freqbin*chan,freqbin*(chan+1)-1)
            print 'Splitting spw %s into file %s'%(spw,newvis)
            split(vis=vis,outputvis=newvis,datacolumn='corrected',spw=spw,width=1,timebin='0s',uvrange='',correlation='',keepflags=True)
            clearcal(newvis)
            splitvises.append(newvis)
        spw=''
    if doimage:
        #### Initialise list
        threshold=[0,0,0,0,0]
        params = read_config()
        #### New addition - find initial r.m.s. then clean down to it next time
        if dormsfind:
            params = read_config()
        #### Weighting should be the same
            cleanweight=params['cleanweight']   
            robust = params['robust']
            im_uvrange = params['im_uvrange']
        #### Halve the resolution, keeping image size the same
            imsize = params['imsize']
            imsize = [int(float(imsize[0])/2),int(float(imsize[1])/2)]
        #### Original
            cell = params['cell']
            scell = re.split('arcmin',cell)
            ncell = float(scell[0])*2.0
            scell = str(ncell)+'arcmin'
            cell = [scell,scell]
            niter = params['niter']
        #### Fast options
            wprojplanes = 1
            facets = 1
            cyclefactor = 1.5
        #### Unchanged
            psfmode = params['psfmode']
            imagermode = params['imagermode']
            mode = params['mode']
            gridmode = params['gridmode']
            out_images = []
            out_stokes = []
            beam_images = []
            beam_stokes = []
            Ext_label = []
            print cell
        #### Find noise for each polarisation, since it can be quite different
            all_stokes = params['stokes']
            s = 0
            for stokes in all_stokes:
                imagename = working_dir+'/'+'preview'
#                params = read_config()
                threshold[s] = params['threshold']
                thresh=str(threshold[s])+'Jy'
                print 'Imaging a preview image to measure r.m.s. with settings: imsize '+str(imsize)+', cell = '+str(cell)+', niter = '+str(niter)+', clean threshold = '+thresh+', wprojplanes = '+str(wprojplanes)+', stokes= '+stokes
                clean(vis=vis,imagename=imagename,mode=mode,gridmode=gridmode, wprojplanes=wprojplanes, facets=facets, niter=niter,threshold=thresh[s],psfmode=psfmode,imagermode=imagermode,cyclefactor=cyclefactor,interactive=False,cell=cell,imsize=imsize,stokes=stokes,weighting=cleanweight,robust=robust,pbcor=False, selectdata=True, uvrange=im_uvrange)
        #### Mask out the central 50% of the beam to avoid source confusion
                if not(os.path.exists('temp.beam')):
        #### Don't make the beam again if it already exists
                    file_made = pbcor('preview.image', obsid, outname='temp.beam')
        #### We don't need the automatically-generated beam fits file
                    os.system('rm beam_temp.beam.fits')
                ia.open('preview.image')
        #### And any sources > 5-6 sigma (i.e. -min of the image)
                ia.calcmask(mask='(preview.image < (-min(preview.image)))&&(temp.beam<(0.5*max(temp.beam)))',name='msk')
                ia.done()
        #### Measure first-pass r.m.s.
                my_output=imstat('preview.image')
                foundrms=my_output['rms']
        #### Set threshold from measured r.m.s.
                threshold[s] = 3*foundrms[0]
                print 'Measured r.m.s. of masked image as '+str(foundrms[0])+'Jy'
                print 'Setting clean threshold to 3*r.m.s.= '+str(threshold[s])+'Jy'
                s+=1
        #### Delete preview images
                rmtables('preview*')
        #### Delete preview beam
            rmtables('temp*')
        #### NITER should be high, as we are now cleaning down to the noise
            niter=20000
        else:
            params = read_config()
            all_stokes = params['stokes']
            s=0
            for stokes in all_stokes:
                threshold[s] = params['threshold']
                s+=1
            niter = params['niter']
        #### Imager settings ####
        #### Move these and other settings to a parset file outside the script.
        params = read_config() 
        im_uvrange = params['im_uvrange']
        cleanweight=params['cleanweight']   
        imsize = params['imsize']
        cell = params['cell']
        robust = params['robust']
        wprojplanes = params['wprojplanes']
        facets = params['facets']
#        threshold = params['threshold']
        psfmode = params['psfmode']
        cyclefactor = params['cyclefactor']
        imagermode = params['imagermode']
        mode = params['mode']
        gridmode = params['gridmode']
        doStokesI = params['doStokesI']
        out_images = []
        out_stokes = []
        beam_images = []
        beam_stokes = []
        Ext_label = []
        ###################################
        # Image the total bandwidth image #
        s=0
        #file_identifier = filename.split('.')[0].split('_')[-1]
        file_identifier = obsid
        for stokes in all_stokes:
          if stokes == 'XX' or 'YY':
            imagename = working_dir+'/'+'f_all_'+stokes
            thresh=str(threshold[s])+'Jy'
            print 'Imaging full bandwidth image with settings: imsize = '+str(imsize)+', cell = '+str(cell)+', niter = '+str(niter)+', clean threshold = '+thresh + ', wprojplanes = '+str(wprojplanes) + ', Stokes= '+str(stokes)
            clean(vis=vis,imagename=imagename,mode=mode,gridmode=gridmode, wprojplanes=wprojplanes, facets=facets, niter=niter, threshold=thresh, psfmode=psfmode,imagermode=imagermode,cyclefactor=cyclefactor,interactive=False,cell=cell,imsize=imsize,stokes=stokes,weighting=cleanweight,robust=robust,pbcor=False,selectdata=True, uvrange=im_uvrange)
            outimage=imagename+'_'+file_identifier+'_'+field_name+'_'+stokes+'.fits'
            exportfits(fitsimage=outimage,imagename=imagename+".image",stokeslast=False,overwrite=True)
            out_images.append(outimage)
            out_stokes.append(stokes)
            Ext_label.append(imagename)
            s+=1
            ### Primary beam ###
            if dopbcor:
                print "generating fullband pbcor image from",imagename+'.image'
                print "output to ",imagename+'_'+file_identifier
                file_made = pbcor(imagename+'.image', obsid, outname=imagename+'_pb.image')
                beam_images.append(file_made)
                beam_stokes.append(stokes)
          ##### Stokes I image #####
        if doStokesI:
               stokes = 'I'
               imagename = working_dir+'/'+'f_all_'+stokes
               print 'Generating Stokes I image using immath (function:autoreduce)'
               XXYYimages = []
               for IM in Ext_label:
                   XXYYimages.append(IM+'.image')
                   XXYYimages.append(IM+'_pb.image')
               immath(imagename=XXYYimages,expr='((IM0*IM1)+(IM2*IM3))/(IM1+IM3)', outfile=imagename+'.image')
               outimage=imagename+'_'+file_identifier+'_'+field_name+'_'+stokes+'.fits'
               exportfits(fitsimage=outimage,imagename=imagename+".image",stokeslast=False,overwrite=True)
               out_images.append(outimage)
               out_stokes.append(stokes)
               Ext_label.append(imagename)
               if dopbcor:
                   print "pbcor on ",imagename+'.image'
                   file_made = pbcor(imagename+'.image', obsid, outname=imagename+'_pb.image')
                   beam_images.append(file_made)
                   beam_stokes.append(stokes)
        ##### Image each sub-band file #####
        if dosub:
            for vis in splitvises:
                visroot,ext=os.path.splitext(os.path.basename(vis)) #get the visibility file root name
                s=0
                for stokes in all_stokes:
                  if stokes == 'XX' or 'YY':
                 ### Assume the noise goes as sqrt(bandwidth), so if bandwidth is divided by n, noise goes up as sqrt(n)
                    thresh=str(threshold[s]*sqrt(nfreqs))+'Jy'
                    print 'Now imaging '+vis+' in stokes '+stokes+' to clean threshold '+thresh
                    imagename=working_dir+'/'+visroot+'_'+stokes
                    clean(vis=vis,imagename=imagename,mode=mode,gridmode=gridmode, wprojplanes=wprojplanes,facets=facets, niter=niter,threshold=thresh, psfmode=psfmode,imagermode=imagermode,cyclefactor=cyclefactor,interactive=False,cell=cell,imsize=imsize,stokes=stokes,weighting=cleanweight,robust=robust,pbcor=False, selectdata=True, uvrange=im_uvrange) 
                    outimage=imagename+'_'+file_identifier+'_'+field_name+'.fits'
                    exportfits(fitsimage=outimage,imagename=imagename+".image",stokeslast=False,overwrite=True)
                    out_images.append(outimage)
                    out_stokes.append(stokes)
                    Ext_label.append(imagename)
                    ### Primary beam ###
                    if dopbcor:
                        pbout = os.path.basename(imagename)
                        file_made = pbcor(imagename+'.image', obsid, outname=imagename+'_pb.image')
                        beam_images.append(file_made)
                        beam_stokes.append(stokes)
                    s+=1
          ##### Stokes I image #####
                if doStokesI:
                    stokes = 'I'
                    imagename = working_dir+'/'+visroot+'_'+stokes
                    print 'Generating Stokes I image using immath (function:autoreduce)'
                    XXYYimages = []
                    for IM in Ext_label:
                        XXYYimages.append(IM+'.image')
                        XXYYimages.append(IM+'_pb.image')
                    immath(imagename=XXYYimages,expr='(IM0*IM1)+(IM2*IM3)/(IM1+IM3)', outfile=imagename+'.image')
                    outimage=imagename+'_'+file_identifier+'_'+field_name+'_'+stokes+'.fits'
                    exportfits(fitsimage=outimage,imagename=imagename+".image",stokeslast=False,overwrite=True)
                    out_images.append(outimage)
                    out_stokes.append(stokes)
                    Ext_label.append(imagename)
                    if dopbcor:
                       print 'pbcor conversion on ',imagename+'.image'
                       file_made = pbcor(imagename+'.image', obsid, outname=imagename+'_pb.image')
                       beam_images.append(file_made)
                       beam_stokes.append(stokes)
          ###########################
            print 'Finished imaging all subbands (function:autoreduce)'
        else:
            print 'Skipping subband image production stage (function:autoreduce)'
        ######### Merge fits files ##########
        cube = params['cube']
        if cube:
		print 'Merging all images in to one fits image (function:autoreduce)'
		print 'INFO: Each subband will be stored as a seprerate Extension'
		print 'INFO: In ds9 click: Open Other > Open Multi Ext as Data Cube - to view subbands.'
		merge_all_fits(out_images, out_stokes, file_identifier+'.fits', Ext_label)
		print 'Merging beam files together'
		merge_all_fits(beam_images, beam_stokes,'beam_'+file_identifier+'.fits', Ext_label)
		print 'Moving final image(s) to results folder ('+out_dir+')'
		shutil.copy(UVFITS_Scratch+file_identifier+'.fits',out_dir)
		shutil.copy(UVFITS_Scratch+'beam_'+file_identifier+'.fits',out_dir)
        else:
                print 'Copying all files to results dir (not creating cube)'
                try:
                    for im_file in out_images:
                        shutil.copy(im_file,out_dir)
                    for bm_file in beam_images:
                        shutil.copy(bm_file,out_dir)
                except:pass
        #####################################
    print 'Finished Successfully'

############################################################################
def autoflag(vis,expedition):
    '''
    Perform automatic visibility flagging, including the DC spikes in each coarse channel, the gaps between the channels and the bad X13 inputs
    '''
    if not os.path.exists(vis):
        print "Vis does not exist",vis
        return
    print 'Using suggested flags for '+str(expedition)+' (function:autoflagger)'
    flagDC(vis)
    flagChanGaps(vis)
    tflagdata(vis=vis,mode='quack',quackinterval=4,quackmode='beg')

    if expedition=="X13":
       print 'Applying X13 flags.'
       flagBadCorrs(vis)
       tflagdata(vis=vis,flagbackup=True,mode='manual',antenna='Tile25')
       tflagdata(vis=vis,flagbackup=True,mode='manual',antenna='Tile23&Tile24')
        ##### flag known bad channels #####
       flagdata(vis=vis,mode='manualflag',flagbackup=True,clipexpr='',spw='0:0;4;192;196;384;388;576;580',antenna='',correlation='')
    if expedition=="X16":
       print 'Applying X16 flags.'
       tflagdata(vis=vis,flagbackup=True,mode='manual',antenna='Tile11')
       tflagdata(vis=vis,flagbackup=True,mode='manual',antenna='Tile15')
       tflagdata(vis=vis,flagbackup=True,mode='manual',antenna='Tile27')
       tflagdata(vis=vis,flagbackup=True,mode='manual',antenna='Tile31')
    if expedition=="Alpha":
       print 'Applying Alpha flags.'
       tflagdata(vis=vis,flagbackup=True,mode='manual',antenna='Tile025')
       tflagdata(vis=vis,flagbackup=True,mode='manual',antenna='Tile035')
    if expedition=="Beta":
       print 'Applying Beta flags.'
       tflagdata(vis=vis,flagbackup=True,mode='manual',antenna='Tile051')
       tflagdata(vis=vis,flagbackup=True,mode='manual',antenna='Tile081')
       tflagdata(vis=vis,flagbackup=True,mode='manual',antenna='Tile085')
       tflagdata(vis=vis,flagbackup=True,mode='manual',antenna='Tile053')
    #############################################
#   Generic flagging applicable to all datasets:

    print 'Running CASA based autoflagger (task:autoflag)' 
    testautoflag(vis=vis, ntime=10, extendflags=false,timecutoff=4.0, freqcutoff=3.0, usepreflags=True, datacolumn='data', writeflags=True)
    flagautocorr(vis)
    tflagdata(vis=vis,mode='tfcrop')

################ flagDC ####################

def flagDC(vis):
    print 'Flagging DC spikes in coarse channel (function:flagDC)'
    chans=numpy.array(range(24))*32+16
    spw=','.join(["0:%s"%ch for ch in chans])
    tflagdata(vis=vis,flagbackup=True,mode='manualflag',spw=spw)

############# flagChanGaps #################

def flagChanGaps(vis):
    print 'Flagging channel gaps (function:flagChanGaps)'
    bchan=numpy.array(range(24))*32
    echan=bchan+2
    spl=[]
    for i in range(24):
        spl.append("0:%s~%s"%(bchan[i],echan[i]))

    spw=','.join(spl)
    tflagdata(vis=vis,flagbackup=True,mode='manualflag',spw=spw)

    bchan=numpy.array(range(24))*32+29
    echan=echan+31
    spl=[]
    for i in range(24):
        spl.append("0:%s~%s"%(bchan[i],echan[i]))
    
    spw=','.join(spl)
    tflagdata(vis=vis,flagbackup=True,mode='manualflag',spw=spw)

############### autocal ##################

def autocal(vis):
    '''
    Function to automatically calibrate the data. This function will use setjy or you can define a cl file to calibrate off
    '''
    params  = read_config()
    refant  = params['refant']
    bsolint = params['bsolint']
    cal_uvrange = params['cal_uvrange']
    cal_loc = params['cal_loc']
    cal_method = params['cal_method']
    minsnr  = params['minsnr']  
    calflux = params['calflux']
    calspex = params['calspex']
    calfreq = params['calfreq']
    print 'Calibrating with settings: ref antenna = '+str(refant)+' , bsolint = '+str(bsolint)+', uvrange = '+str(cal_uvrange)+', minsnr = '+str(minsnr)+' (funtion:autocal)'
    caltable='temp'
    #clearcal(vis)
    if   cal_method == 1:
            print 'Using setjy method (function:autocal)'
            setjy(vis=vis,fluxdensity=calflux, spix=calspex, reffreq=calfreq, field='0')
            bcal=caltable+'.bcal'
            if os.path.exists(bcal):
               rmtables(bcal)
            bandpass(vis=vis,caltable=bcal,solint=bsolint,refant=refant,bandtype='B',append=False,selectdata=True,uvrange=cal_uvrange,minsnr=minsnr)
            applycal(vis=vis,selectdata=False,gaintable=bcal)
    elif cal_method == 2:
            print 'Using cl method (function:autocal)'
            im.open(vis,usescratch=True)
            im.ft(complist=cal_loc)
            im.close()
            bcal=caltable+'.bcal'
            if os.path.exists(bcal):
               rmtables(bcal)
            bandpass(vis=vis,caltable=bcal,solint=bsolint,refant=refant,bandtype='B',append=False,selectdata=True,uvrange=cal_uvrange,minsnr=minsnr)
            applycal(vis=vis,selectdata=False,gaintable=bcal)
    elif cal_method == 3:
            print 'Using copy solutions method (function:autocal)'
            #bandpass(vis=vis,caltable=cal_loc,solint=bsolint,refant=refant,bandtype='B',append=False,selectdata=True,uvrange=cal_uvrange,minsnr=minsnr)
            applycal(vis=vis,selectdata=False,gaintable=cal_loc)
    elif cal_method == 4:
            try:
                calrepo = params['calrepo']
                cal_dtmax = params['cal_dtmax']
            except(IndexError):
                print "calibration parameters not set correctly, see error below"
                raise
            print 'searching cal repo %s for best calibration'%calrepo
            observation_number = int(os.path.basename(vis).split('.')[0]) #assume the file is generated by convert_ngas
            calfiles = glob.glob(calrepo+'/1*.cal')
            available_cals = [int(os.path.basename(s)[:-4]) for s in calfiles]
            print "found %d cals in %s like %s"%(len(available_cals),calrepo,available_cals[0])
            calobsnum = find_best_cal(observation_number,cal_dtmax=cal_dtmax,available_cals=available_cals,relax=True)
            if calobsnum is None:
                return 1
            cal_loc = "%s/%s.cal"%(calrepo,calobsnum)
            print "applying cal file %s"%cal_loc
            applycal(vis=vis,selectdata=False,gaintable=cal_loc)
            return 0
########### Flag Bad Corrs ############

def flagBadCorrs(vis):
    print 'Flagging bad correlations: (function:flagBadCorrs)'
    badinps=[( 0,62), 
( 1,61), ( 1,62), 
( 2,60), ( 2,61), ( 2,62), 
( 3,59), ( 3,60), ( 3,61), ( 3,62), 
( 4,58), ( 4,59), ( 4,60), ( 4,61), ( 4,62), 
( 5,57), ( 5,58), ( 5,59), ( 5,60), ( 5,61), ( 5,62), 
( 6,56), ( 6,57), ( 6,58), ( 6,59), ( 6,60), ( 6,61), ( 6,62), 
( 7,55), ( 7,56), ( 7,57), ( 7,58), ( 7,59), ( 7,60), ( 7,61), ( 7,62), 
( 8,54), ( 8,55), ( 8,56), ( 8,57), ( 8,58), ( 8,59), ( 8,60), ( 8,61), ( 8,62), 
( 9,53), ( 9,54), ( 9,55), ( 9,56), ( 9,57), ( 9,58), ( 9,59), ( 9,60), ( 9,61), ( 9,62), 
(10,52), (10,53), (10,54), (10,55), (10,56), (10,57), (10,58), (10,59), (10,60), (10,61), (10,62), 
(11,51), (11,52), (11,53), (11,54), (11,55), (11,56), (11,57), (11,58), (11,59), (11,60), (11,61), (11,62), 
(12,50), (12,51), (12,52), (12,53), (12,54), (12,55), (12,56), (12,57), (12,58), (12,59), (12,60), (12,61), (12,62), 
(13,49), (13,50), (13,51), (13,52), (13,53), (13,54), (13,55), (13,56), (13,57), (13,58), (13,59), (13,60), (13,61), (13,62), 
(14,48), (14,49), (14,50), (14,51), (14,52), (14,53), (14,54), (14,55), (14,56), (14,57), (14,58), (14,59), (14,60), (14,61), (14,62), 
(16,62), 
(17,61), (17,62), 
(18,60), (18,61), (18,62), 
(19,59), (19,60), (19,61), (19,62), 
(20,58), (20,59), (20,60), (20,61), (20,62), 
(21,57), (21,58), (21,59), (21,60), (21,61), (21,62), 
(22,56), (22,57), (22,58), (22,59), (22,60), (22,61), (22,62), 
(23,55), (23,56), (23,57), (23,58), (23,59), (23,60), (23,61), (23,62), 
(24,54), (24,55), (24,56), (24,57), (24,58), (24,59), (24,60), (24,61), (24,62), 
(25,53), (25,54), (25,55), (25,56), (25,57), (25,58), (25,59), (25,60), (25,61), (25,62), 
(26,52), (26,53), (26,54), (26,55), (26,56), (26,57), (26,58), (26,59), (26,60), (26,61), (26,62), 
(27,51), (27,52), (27,53), (27,54), (27,55), (27,56), (27,57), (27,58), (27,59), (27,60), (27,61), (27,62), 
(28,50), (28,51), (28,52), (28,53), (28,54), (28,55), (28,56), (28,57), (28,58), (28,59), (28,60), (28,61), (28,62), 
(29,49), (29,50), (29,51), (29,52), (29,53), (29,54), (29,55), (29,56), (29,57), (29,58), (29,59), (29,60), (29,61), (29,62), 
(30,48), (30,49), (30,50), (30,51), (30,52), (30,53), (30,54), (30,55), (30,56), (30,57), (30,58), (30,59), (30,60), (30,61), (30,62), 
(32,62), 
(33,61), (33,62), 
(34,60), (34,61), (34,62), 
(35,59), (35,60), (35,61), (35,62), 
(36,58), (36,59), (36,60), (36,61), (36,62), 
(37,57), (37,58), (37,59), (37,60), (37,61), (37,62), 
(38,56), (38,57), (38,58), (38,59), (38,60), (38,61), (38,62), 
(39,55), (39,56), (39,57), (39,58), (39,59), (39,60), (39,61), (39,62), 
(40,54), (40,55), (40,56), (40,57), (40,58), (40,59), (40,60), (40,61), (40,62), 
(41,53), (41,54), (41,55), (41,56), (41,57), (41,58), (41,59), (41,60), (41,61), (41,62), 
(42,52), (42,53), (42,54), (42,55), (42,56), (42,57), (42,58), (42,59), (42,60), (42,61), (42,62), 
(43,51), (43,52), (43,53), (43,54), (43,55), (43,56), (43,57), (43,58), (43,59), (43,60), (43,61), (43,62), 
(44,50), (44,51), (44,52), (44,53), (44,54), (44,55), (44,56), (44,57), (44,58), (44,59), (44,60), (44,61), (44,62), 
(45,49), (45,50), (45,51), (45,52), (45,53), (45,54), (45,55), (45,56), (45,57), (45,58), (45,59), (45,60), (45,61), (45,62), 
(46,48), (46,49), (46,50), (46,51), (46,52), (46,53), (46,54), (46,55), (46,56), (46,57), (46,58), (46,59), (46,60), (46,61), (46,62), 
(48,62), 
(49,61), (49,62), 
(50,60), (50,61), (50,62), 
(51,59), (51,60), (51,61), (51,62), 
(52,58), (52,59), (52,60), (52,61), (52,62), 
(53,57), (53,58), (53,59), (53,60), (53,61), (53,62), 
(54,56), (54,57), (54,58), (54,59), (54,60), (54,61), (54,62), 
(55,63), (55,56), (55,57), (55,58), (55,59), (55,60), (55,61), (55,62), 
(56,54), (56,55), (56,63), (56,57), (56,58), (56,59), (56,60), (56,61), (56,62), 
(57,53), (57,54), (57,55), (57,56), (57,63), (57,58), (57,59), (57,60), (57,61), (57,62), 
(58,52), (58,53), (58,54), (58,55), (58,56), (58,57), (58,63), (58,59), (58,60), (58,61), (58,62), 
(59,51), (59,52), (59,53), (59,54), (59,55), (59,56), (59,57), (59,58), (59,63), (59,60), (59,61), (59,62), 
(60,50), (60,51), (60,52), (60,53), (60,54), (60,55), (60,56), (60,57), (60,58), (60,59), (60,63), (60,61), (60,62), 
(61,49), (61,50), (61,51), (61,52), (61,53), (61,54), (61,55), (61,56), (61,57), (61,58), (61,59), (61,60), (61,63), (61,62), 
(62,48), (62,49), (62,50), (62,51), (62,52), (62,53), (62,54), (62,55), (62,56), (62,57), (62,58), (62,59), (62,60), (62,61),(62,63)]
 

    tiledict={}
    poldict={}
    for i in range(64):
        node=(i/16)+1
        pol=(i%2) # 0=Ypol 1=xpol
        slot=(19-((i%16)/2))%8+1
        tiledict[i]=(node+4*(slot-1))
        poldict[i]= "Y" if pol == 0 else "X"


    flagmanager(vis=vis,mode='save',versionname='preflagbadinps',merge='replace')

    XXstr=''
    YYstr=''
    XYstr=''
    #YXstr=''

    for (t1,t2) in badinps:

        if tiledict[t1] < tiledict[t2]:
            antenna='Tile%02i'%tiledict[t1]+"&"+'Tile%02i'%tiledict[t2]+';'
            correlation=poldict[t1]+poldict[t2]
        else:
            antenna='Tile%02i'%tiledict[t2]+"&"+'Tile%02i'%tiledict[t1]+';'
            correlation=poldict[t2]+poldict[t1]
        
        if correlation=='XX':
            XXstr+=antenna
        elif correlation=='YY':
            YYstr+=antenna
        elif correlation=='XY' or correlation=='YX':
            XYstr+=antenna


    print 'XX: ',XXstr
    print ""
    print 'YY: ',YYstr
    print ""
    print 'XY: ',XYstr
    print ""

    if len(XXstr) > 0:
        flagdata(vis=vis,flagbackup=False,correlation='XX',mode='manualflag',clipexpr='',field='',selectdata=True,antenna=XXstr[:-1],async=False)
    if len(YYstr) > 0:
        flagdata(vis=vis,flagbackup=False,correlation='YY',mode='manualflag',clipexpr='',field='',selectdata=True,antenna=YYstr[:-1],async=False)
    if len(XYstr) > 0:
        flagdata(vis=vis,flagbackup=False,correlation='XY',mode='manualflag',clipexpr='',field='',selectdata=True,antenna=XYstr[:-1],async=False)
        flagdata(vis=vis,flagbackup=False,correlation='YX',mode='manualflag',clipexpr='',field='',selectdata=True,antenna=XYstr[:-1],async=False)

############################################

def psffits(fitsfile):
    head,tail=os.path.split(fitsfile)
    root,ext=os.path.splitext(tail)
    psfimage=os.path.join(head,root+".psf")
    exportfits(imagename=psfimage,fitsimage=os.path.join(head,root+"_psf.FITS"),stokeslast=False,overwrite=True)

############################################

def modfits(fitsfile):
    head,tail=os.path.split(fitsfile)
    root,ext=os.path.splitext(tail)
    modimage=os.path.join(head,root+".model")
    exportfits(imagename=modimage,fitsimage=os.path.join(head,root+"_model.FITS"),stokeslast=False,overwrite=True)

############################################

def residfits(fitsfile):
    head,tail=os.path.split(fitsfile)
    root,ext=os.path.splitext(tail)
    residimage=os.path.join(head,root+".residual")
    exportfits(imagename=residimage,fitsimage=os.path.join(head,root+"_resid.FITS"),stokeslast=False,overwrite=True)

############################################

def allfits(fitsfile):
    psffits(fitsfile)
    modfits(fitsfile)
    residfits(fitsfile)

###########################################

def merge_all_fits(images,current_stokes,totalfitsoutname,Ext_label):
    '''
    Function to merge singular image fits produced by the pipeline into *one* master fits image.
    Each seperate polarisation and frequency will be stroed as a seperate extension. 
    The task relies on fits_utils.py being available. This task will also add the nessacary metadata
    so that the images are compatible with the VAST transients pipeline.  
    '''
    #### Add some stats to the headers ####
    for i in range(len(images)):
        print 'Updating header in '+images[i]
        fitsimage=FU.FITSImage(filename=images[i])
        m,s,mn,mx=fitsimage.printstatistics()
        fitsimage.updateheader(key=['IMAGEMED','IMAGESTD','IMAGEMIN','IMAGEMAX'],
                             value=[m,s,mn,mx],comment=['[Jy/beam] Image median','[Jy/beam] Image rms',
                                                        '[Jy/beam] Image minimum','[Jy/beam] Image maximum'])
        fitsimage.updateheader(key=['STOKES'],value=[current_stokes[i]],comment=[''])
     ####### Merge all files into one master fits file  ###########
    FU.mergefitsfiles(totalfitsoutname, images, Ext_label)
############################################

def pbcor(imagename, obsnum, outname):
    '''
    Task to generate pb maps.
    '''
    print 'Generating primary beam map (function:pbcor)'
    file_identifier = obsnum#file.split('.')[0].split('_')[-1]
#    all_delays = read_delays(delays_file)
#    If you don't find the delays, try adding a second and looking again -- up to 10 seconds
#    n=0
#    delta=timedelta(microseconds=1000000)
#    while (n<=10):
#        dt=datetime(int(file_identifier[0:4]),int(file_identifier[4:6]),int(file_identifier[6:8]),int(file_identifier[8:10]),int(file_identifier[10:12]),int(file_identifier[12:14]))
#        testtime=dt+(n*delta)
#        str_testtime=testtime.strftime("%Y%m%d%H%M%S")
#        if all_delays.has_key(str_testtime):
#           delays = all_delays[str_testtime]
#           n=10
#        else:
#           n+=1

#    if ((not(all_delays.has_key(str_testtime)))and(n==10)):

    # Get the delays from the database
    # If it's a new-style obervation in GPS seconds, just use the number

    if not re.match('[0-9]{10}',file_identifier):
        obsnum=mwapy.get_observation_info.find_observation_num(file_identifier,db=db)
    else:
        obsnum=int(file_identifier)
    info=mwapy.get_observation_info.MWA_Observation(obsnum,db=db)

    delays=info.delays

    if not delays :
       print "Delays not found... setting to zenith."
       delays = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

    pbgain(imagename=imagename, pbimage=outname, delays=delays)
    path,filename = os.path.splitext(outname)
    outname = os.path.join(path,'beam_'+filename+'.fits')
    exportfits(fitsimage=outname,imagename=outname,stokeslast=False,overwrite=True)
    return 'beam_'+outname+'.fits'


############################################

#def read_delays(delays_file):
#    print 'Reading the delay file (function:read_delays)'
#    '''
#    Load the delays from a text file. The file format is a CSV eg:
#    
#      HydA_121_20100322153930, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
#      HydA_121_20100322154530, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
#      
#    Returns a dictionary of {'key': delays} where:
#      key: the date-time of the data block that the delays apply to (string) eg '20100322153930'
#      delays: a list of delays (integers)
#    '''
#    delay_dict = {}
#    reader = csv.reader(open(delays_file))
#    for row in reader:
#        key=row[0].split('_')[-1]
#        interim_delays = [int(s) for s in row[1:17]]
#        delay_dict[key] = interim_delays
#
#    return delay_dict

############ Run the code ##################
UVFITS_Scratch = 'SIP_scratch'
MDIR = os.getcwd()
try: 
    print "processing ",len(myobslist)," observations"
except(NameError):
    myobslist = [s.strip() for s in open(OBSLIST, "r").readlines()]
    print "processing ",len(myobslist)," observations from ",OBSLIST
print '---------------------------------'
print 'MWA 32T Standard Imaging Pipeline'
print '---------------------------------'
run_logtime = time.strftime('%Y%m%d-%H%M')
params = read_config()
results_folder_prefix = params['results_folder_prefix']
#os.mkdir(out_dir)

for obsid in myobslist:
    working_dir = os.path.join(MDIR,obsid,results_folder_prefix+'_'+run_logtime)
    out_dir = os.path.join(MDIR,obsid,'images')
    try:os.mkdir(out_dir)
    except(OSError):pass
    try: os.mkdir(working_dir)
    except(OSError):pass
#    filename = obspath.split('/')[-1]
#    print 'Processing '+filename
#    os.system('rm -rf '+UVFITS_Scratch+'/*')
#    print 'Removed contents of scratch folder from previous run.'
#    shutil.copy(obspath,UVFITS_Scratch)
#    print 'Copying uvfits file to scratch area'
    print "processing obsid = %s"%obsid
    dopbcor = params['dopbcor']  
    dormsfind = params['dormsfind']  
    dosub = params['dosub']
    doimage= params['doimage']
    expedition = params['expedition']
    os.chdir(obsid)
    autoreduce(obsid=obsid, expedition=expedition, dosub=dosub, doimage=doimage, dopbcor=dopbcor,
                working_dir=working_dir,out_dir=out_dir)
    os.chdir('..')
del(myobslist)

############################################



