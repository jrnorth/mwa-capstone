from pylab import *
import re
import numpy as n,os,sys,shutil

#-------------------Creating the UTC date in the plot title---------
# From http://casaguides.nrao.edu/index.php?title=Formats_for_Time
def time_convert(mytime, myunit='s'):
    if type(mytime).__name__ <> 'list': mytime=[mytime]
    myTimestr = []
    for time in mytime:
        q1=qa.quantity(time,myunit)
        time1=qa.time(q1,form='ymd')
        myTimestr.append(time1)
    return myTimestr

#--Testing depth of arrays since CASA changes version-to-version --

depth = lambda L: isinstance(L, list) and max(map(depth, L))+1

#-------------Populate useful arrays-------------------------------

spw=caltable+'/SPECTRAL_WINDOW'
ants=caltable+'/ANTENNA'
field=caltable+'/FIELD'
cal_root=re.sub('.cal','',caltable)

tb.open(caltable)

# NB: Won't work with CASA 3.3 and below
G = tb.getcol('CPARAM')
M = tb.getcol('FLAG')
SNR = n.ma.array(tb.getcol('SNR').squeeze(),mask=M.squeeze())
tb.close()

tb.open(spw)
F=tb.getcol('CHAN_FREQ')
tb.close()

tb.open(ants)
Tile=tb.getcol('NAME')
tb.close()

tb.open(field)
obs_time=tb.getcol('TIME')[0]
calibrator=tb.getcol('NAME')[0]
tb.close()

#--------------------Prepare new calibration tables-----------
# A 'model' table, with fitted amplitudes (5th order polynomial) and phases (1st order polynomial)
# A 'clipped' table, where the high-amplitude points have been removed by comparison to the model
# A 'test' table, where the phase has been fitted, but the amplitude allowed to remain the same

model_gains = n.empty(shape=(shape(G)), dtype=complex128)
test_gains = n.empty(shape=(shape(G)), dtype=complex128)

clip_flags = n.empty(shape=(shape(M)), dtype=bool)

test_caltable=re.sub('.cal','_test.cal',caltable)
model_caltable=re.sub('.cal','_model.cal',caltable)
clip_caltable=re.sub('.cal','_clip.cal',caltable)

for table in [test_caltable,model_caltable,clip_caltable]:
    if os.path.exists(table):
        shutil.rmtree(table)
    shutil.copytree(caltable,table)

#--------------------Plot options--------------------------
phase_png=re.sub('.cal','_phases.png',caltable)
snr_png=re.sub('.cal','_snr.png',caltable)
amp_png=re.sub('.cal','_amp.png',caltable)

for png in [phase_png,snr_png,amp_png]:
    if os.path.exists(png):
       os.remove(png)

sbplt_pad_left  = 0.125  # the left side of the subplots of the figure
sbplt_pad_right = 0.9    # the right side of the subplots of the figure
sbplt_pad_bottom = 0.1   # the bottom of the subplots of the figure
sbplt_pad_top = 0.9      # the top of the subplots of the figure
sbplt_pad_wspace = 0.2   # the amount of width reserved for blank space between subplots
sbplt_pad_hspace = 0.5   # the amount of height reserved for white space between subplots

# Roughly 2:1 columns to rows
subplot_cols=n.round(n.sqrt(G.shape[2])*1.4)
subplot_rows=n.round(n.sqrt(G.shape[2])/1.4)

figsize=(15.875,7.775)
phsfig = figure(figsize=figsize)
ampfig = figure(figsize=figsize)

# Scale amplitude plots to the same, maximum gain 
maxamp=n.max(n.abs(G))

# Compatibility with different versions of CASA
#Numpy array
try:
   minfreq=F[0][0][0]
   maxfreq=F[F.size-1][0][0]
except:
   minfreq=F[0][0]
   maxfreq=F[F.size-1][0]

#Python list
if depth(time_convert(obs_time))==2:
   obs_time_wst=time_convert(obs_time)[0][0]
   obs_time_utc=time_convert(obs_time+8*60*60)[0][0]
elif depth(time_convert(obs_time))==1:
   obs_time_wst=time_convert(obs_time)[0]
   obs_time_utc=time_convert(obs_time+8*60*60)[0]

phase_title="{0:s}: {1:s} @ {2:3.0f}--{3:3.0f}MHz: {4:s} UTC ({5:s} WST)".format(cal_root,calibrator,(minfreq/1e6),(maxfreq/1e6),obs_time_wst,obs_time_utc)

amp_title="{0:s}: {1:s} @ {2:3.0f}--{3:3.0f}MHz: {4:s} UTC ({5:s} WST): Scale = 0--{6:2.1f}".format(cal_root,calibrator,(minfreq/1e6),(maxfreq/1e6),obs_time_wst,obs_time_utc,maxamp)

# XX raw data and fit in green; YY raw data and fit in red
datacolor=('g','r')
fitcolor=('c','m')
legend_position=(0.50,0.95)

# XX, YY labels. assuming XX=0 and YY=1 !!
pol_label=('XX','YY')

#--------------------------------------------------------------

for antenna in range(G.shape[2]):
    for pol in range(G.shape[0]):
      unwrapflag=False
      amps=n.ma.array(n.abs(G[pol,:,antenna]),mask=M[pol,:,antenna])
      angles=n.ma.array(n.angle(G[pol,:,antenna]),mask=M[pol,:,antenna])
# Fit first-order polynomial to phases
      P,res,rank,sv,cond = n.ma.polyfit(n.ma.array(F[:,0]),angles,1,full=True)
# Fit fith-order polynomial to amplitudes
      A,res_a,rank,sv,cond = n.ma.polyfit(n.ma.array(F[:,0]),amps,5,full=True)
# Make a model line
      phsmodel = n.poly1d(P)
      ampmodel = n.poly1d(A)
      style='+'
# If the delay is crazy, add 90 degrees to the phase and re-fit (safer than unwrapping)
      if (res>200):
        unwrapflag=True
        angles=n.ma.array(n.angle(G[pol,:,antenna]*(complex(0,1))),mask=M[pol,:,antenna])
        P,res,rank,sv,cond = n.ma.polyfit(n.ma.array(F[:,0]),angles,1,full=True)
        if (res<200):
# Make a new model line
           phsmodel = n.poly1d(P)
# Take the 90 degrees back out
           test_gains[pol,:,antenna]=amps*n.cos(phsmodel(F[:,0])-(n.pi/2)) + complex(0,1)*amps*n.sin(phsmodel(F[:,0])-(n.pi/2))
        else:
# If the delay is *still* crazy, subtract 90 degrees to the phase and re-fit (safer than unwrapping)
           if (res>200):
              angles=n.ma.array(n.angle(G[pol,:,antenna]*(complex(0,-1))),mask=M[pol,:,antenna])
              P,res,rank,sv,cond = n.ma.polyfit(n.ma.array(F[:,0]),angles,1,full=True)
              if (res<200):
# Make a new model line
                 phsmodel = n.poly1d(P)
# Put the 90 degrees back in
                 test_gains[pol,:,antenna]=amps*n.cos(phsmodel(F[:,0])+(n.pi/2)) + complex(0,1)*amps*n.sin(phsmodel(F[:,0])+(n.pi/2))
# If it didn't fit at all, it must have a fast phase wrap and can't be fit by this method
              else:
                 print "crazy phase for "+Tile[antenna]+" pol "+pol_label[pol]+": not writing to test table"
                 test_gains[pol,:,antenna]=G[pol,:,antenna]
                 unwrapflag=False
# Bad fits are shown as dashed lines
                 style='--'
      else:
        test_gains[pol,:,antenna]=amps*n.cos(phsmodel(F[:,0])) + complex(0,1)*amps*n.sin(phsmodel(F[:,0]))
# Phase plot
      ax = phsfig.add_subplot(subplot_rows,subplot_cols,antenna+1)
      ax.set_title(Tile[antenna],fontsize=10)
# Amplitude plot
      ax1 = ampfig.add_subplot(subplot_rows,subplot_cols,antenna+1)
      ax1.set_title(Tile[antenna],fontsize=10)
# Highlight badly-behaved antennas
# First check if the whole thing is flagged
      if (ma.all(M[pol,:,antenna])):
         rect = ax.patch  # a Rectangle instance
         rect.set_facecolor('black')
         rect.set_alpha('0.4')
         rect = ax1.patch  # a Rectangle instance
         rect.set_facecolor('black')
         rect.set_alpha('0.4')
# Or maybe the fit is really bad
      elif (res>200):
         rect = ax.patch  # a Rectangle instance
         rect.set_facecolor('yellow')
         rect.set_alpha('0.2')
         rect = ax1.patch  # a Rectangle instance
         rect.set_facecolor('yellow')
         rect.set_alpha('0.2')
# Or maybe the fit is fine, but the gradient is very shallow
      elif (abs(P[0])<1E-13):
# In that case, if the gains are all flagged, it's dead
         if (round(n.ma.sum(n.ma.array(abs(G[pol,:,antenna]),mask=M[pol,:,antenna])))==0):
           rect = ax.patch  # a Rectangle instance
           rect.set_facecolor('red')
           rect.set_alpha('0.2')
           rect = ax1.patch  # a Rectangle instance
           rect.set_facecolor('red')
           rect.set_alpha('0.2')
           style='--'
# Or if they're not, then it's fine, it must be the reference antenna
         else:
           rect = ax.patch  # a Rectangle instance
           rect.set_facecolor('green')
           rect.set_alpha('0.2')
           rect = ax1.patch  # a Rectangle instance
           rect.set_facecolor('green')
           rect.set_alpha('0.2')
# Need to do the clipping at this stage, before I redo the angles!
# Test whether the amplitude or phase is more than 3sigma away from the fitted models
      sigmaclip = True #change to a user specified option?
      if sigmaclip == True:
         sigma=3.0
         ampmodel_rms=n.std(amps-ampmodel(F[:,0]))
         phsmodel_rms=n.std(angles-phsmodel(F[:,0]))
#         print Tile[antenna],180.*n.mean(phsmodel(F[:,0]))/n.pi,180.*phsmodel_rms/n.pi,ampmodel_rms
         for count in range(0,len(amps)):
            if abs(amps[count]-ampmodel(F[count])[0]) > (sigma*ampmodel_rms) or abs(angles[count]-phsmodel(F[count])[0]) > (sigma*phsmodel_rms):
               clip_flags[pol,count,antenna]=True
            else:
               clip_flags[pol,count,antenna]=M[pol,count,antenna]
# Derive model gains from the amplitude and phase models
      model_gains[pol,:,antenna]=ampmodel(F[:,0])*n.cos(phsmodel(F[:,0])) + complex(0,1)*ampmodel(F[:,0])*n.sin(phsmodel(F[:,0]))

# Reset angles after all the jiggery-pokery above
      angles=n.ma.array(n.angle(G[pol,:,antenna]),mask=M[pol,:,antenna])

# plot amplitudes
      ax1.plot(amps,style+datacolor[pol],ms=2)
      ax1.plot(ampmodel(F[:,0]),style+fitcolor[pol],ms=2)
# plot phases
      ax.plot(angles,style+datacolor[pol],ms=2)
     # Quick check to see if the phase had to be unwrapped
      if (not unwrapflag):
	   # Currently can't plot phase model when I had to 'unwrap' the phase
           ax.plot(phsmodel(F[:,0]),style+fitcolor[pol],ms=2)
# Optional highlighting to show where I tried to unwrap
#      else:
#           rect = ax.patch  # a Rectangle instance
#           rect.set_facecolor('blue')
#           rect.set_alpha('0.2')

# Previous attempt with YY shown with a 90-degree offset for increased visibility
# Looks weird when the phases wrap so discontinued
#      plot(angles+float(pol)*n.pi/2,'.'+datacolor[pol],ms=2)
#      plot(phsmodel(F[:,0])+float(pol)*n.pi/2,style+fitcolor[pol],ms=2)

# Overlay phase offset and delay -- makes the plots very very busy

#      if (phsmodel):
#         textstr="$\phi=${0:3.1f}\n$D=${1:2.1f}".format(rad2deg(phsmodel(F[len(F)/2][0])),phsmodel.coeffs[1])
#         props=dict(boxstyle='round',facecolor=datacolor[pol],alpha=0.5)
#         ax.text(0.05,legend_position[pol],textstr,transform=ax.transAxes,fontsize=4,verticalalignment='top',bbox=props)

# Hide pointless overlapping axis labels
      ax.set_xticks([])
      ax.set_yticks([])
      ax1.set_xticks([])
      ax1.set_yticks([])
      ax.set_ylim([-n.pi,n.pi])
# Set amps to the same scale: the maximum gain across the whole array
      ax1.set_ylim([0,maxamp])
      ax.set_autoscale_on(False)
      ax1.set_autoscale_on(False)

#Introduced in matplotlib1.1 . Tested but it overwrites the title with subplot titles.
#phsfig.tight_layout()
#ampfig.tight_layout()

phsfig.subplots_adjust(left=sbplt_pad_left, bottom=sbplt_pad_bottom, right=sbplt_pad_right, top=sbplt_pad_top, wspace=sbplt_pad_wspace, hspace=sbplt_pad_hspace)
phsfig.suptitle(phase_title,fontsize=16)

ampfig.subplots_adjust(left=sbplt_pad_left, bottom=sbplt_pad_bottom, right=sbplt_pad_right, top=sbplt_pad_top, wspace=sbplt_pad_wspace, hspace=sbplt_pad_hspace)
ampfig.suptitle(amp_title,fontsize=16)

figure(phsfig.number,bbox_inches='tight')
savefig(phase_png)
figure(ampfig.number,bbox_inches='tight')
savefig(amp_png)

#snrfig = figure(figsize=figsize)

# SNR plot -- didn't find very useful
#for antenna in range(SNR.shape[2]):
#    for pol in range(SNR.shape[0]):
#      masked_SNR=n.ma.array(SNR[pol,:,antenna],mask=M[pol,:,antenna])
#      ax1 = subplot(subplot_rows,subplot_cols,antenna+1)
#      plot(masked_SNR,'.'+datacolor[pol],ms=2)
#      ylim(0,n.max(SNR))

#figure(snrfig.number,bbox_inches='tight')
#savefig(snr_png)


# Save gains to new tables

# Clip table uses original phases and amplitudes, but flags clipped amplitudes
tb.open(clip_caltable,nomodify=False)
tb.putcol('CPARAM',G)
tb.putcol('FLAG',clip_flags)
tb.close()

# Test table uses model phases and amplitude clipping
tb.open(test_caltable,nomodify=False)
tb.putcol('CPARAM',test_gains)
tb.putcol('FLAG',clip_flags)
tb.close()

# Model table shows the model
#****including any fits unwrapped phases****
# i.e. do NOT use this to calibrate!
tb.open(model_caltable,nomodify=False)
tb.putcol('CPARAM',model_gains)
tb.putcol('FLAG',M)
tb.close()


