#! /usr/bin/env python
#little script to plot calibration output within ipython --pylab or CASA
#DCJ 14 Dec 2011
#expected environment variables
#calsave = <calfile>.npz (REQUIRED)
#signal_path_file = a file containing the signal path as pasted in from (optional)
# devstuff.mwa32t.org/siteconfig/currentconfiguration
#Values as of 14 Dev 2011 are included alongside this script as 32t_signal_path.txt
#and are used if this is not set
from pylab import *
import numpy as n,os,sys
#calsave = sys.argv[-1]
try:
    from mwacasa.mwa32T.parse_32t_signal_path import import_tile_to_rcvr,__file__
    signalpath=True
except:
    signalpath = False
#load the rcvr-beamformer mapping
if signalpath:
    try:
        signal_path_file
    except(NameError):
        signal_path_file = os.path.join(os.path.dirname(__file__),'32t_signal_path.txt')
    rcvrs = import_tile_to_rcvr(signal_path_file)
def dB(A):
    return 10*n.log10(A)


try:
    F = n.load(calsave)
    M = F['mask']
    G = n.ma.masked_where(M,F['G'])
    freqs = F['freq'].squeeze()
    print M.shape
`<    print freqs.shape
except(IOError):
    print calsave,"not found!"
    G = None
    sys.exit()
print G.shape
pcol = ['.k','.b']
figsize=(15.875,   7.775)
ampfig = figure(figsize=figsize)
phsfig = figure(figsize=figsize)
flagfig = figure(figsize=figsize)
angles = []
#compute phase angles
for i in range(G.shape[2]):
    for pol in range(G.shape[0]):
        angle = n.ma.masked_where(M[pol,:,i],n.unwrap(n.angle(G[pol,:,i]),discont=2.6))
        angles.append(angle)
tp = [0.1,0.75]
angles = n.ma.array(angles).T
print "T,R,delay [ns]"
rcvr_delays = {}
for i in range(G.shape[2]):
    for pol in range(G.shape[0]):
        figure(flagfig.number)
        ax = subplot(6,6,i+1);
        fill_between(freqs,y1=M[pol,:,i])
        
        if pol==0: text(tp[0],tp[1],'%d'%i,transform=ax.transAxes)
        ylim([0,1.3])
        if (i % 6):yticks([]);ylabel('')
        if (G.shape[2]-6)>i: xticks([]);xlabel('')
        else:
            labels = gca().get_xticklabels()
            for label in labels:
                label.set_rotation(30)

            
        figure(ampfig.number)
        ax = subplot(6,6,i+1);
        plot(dB(n.ma.abs(G[pol,:,i].filled(n.nan))),pcol[pol],ms=2)
        P,res,rank,sv,cond = n.ma.polyfit(freqs/1e3,angles[:,i+pol],1,full=True)
        delay = P[0]/(2*n.pi)*1.3 #compensate for speed of light in cable (1.3)  
        if (i % 6):yticks([]);ylabel('')
        if (G.shape[2]-6)>i: xticks([]);xlabel('')
    #    else: xticks(freqs[range(freqs.size/4,freqs.size,freqs.size/3)].astype(int).squeeze().tolist())
        else:
            newxticks = [ax.get_xticks()[m] for m in range(0,len(ax.get_xticks()),2)] 
            xticks(newxticks)
        ylim([dB(n.ma.abs(G[G>0]).min()*0.8),dB(n.ma.abs(G).max(fill_value=0)*1.1)])
        #xlim([freqs.min(),freqs.max()])
        if signalpath: text(tp[0],tp[1],"T:%s, R:%d"%(str(i+1),rcvrs[i+1]),transform=ax.transAxes)
        text(tp[0],tp[1]-0.1*pol,'%4.2fns'%(delay),transform=ax.transAxes)
    
        figure(phsfig.number)
        ax = subplot(6,6,i+1)
        plot(n.angle(G[:,i].filled(n.nan)),'0.5')
        plot(angles[:,i],'.k',ms=2)
        phsmodel = n.poly1d(P)
        plot(phsmodel(freqs/1e3),'0.5')
        if ( i % 6):yticks([]);ylabel('')
        if (G.shape[2]-6)>i: xticks([]);xlabel('')
    #    els e: xticks(freqs[range(freqs.size/4,freqs.size,freqs.size/3)].astype(int).squeeze().tolist())
        else:
    #        newxticks = [ax.get_xticks()[i] for i in range(0,len(ax.get_xticks()),2)]
            #print newxticks
            xticks(newxticks)
        if angles.min()<0:
            ylim([angles.min(fill_value=0)*1.2,angles.max(fill_value=0)*1.1])
        else:
            ylim([angles.min(fill_value=0)*0.8,angles.max(fill_value=0)*1.1])
        ylim([-10,10])
        #xlim([freqs.min(),freqs.max()])
        if signalpath: text(tp[0],tp[1],"T:%s, R:%d"%(str(i+1),rcvrs[i+1]),transform=ax.transAxes)
        text(tp[0],tp[1]-0.1*pol,'%3.2fns'%(delay),transform=ax.transAxes)
        if signalpath: 
            print ',\t'.join([str(i+1),str(rcvrs[i+1]),'%3.2f'%(delay)])
            try: rcvr_delays[rcvrs[i+1]].append(delay)
            except(KeyError): rcvr_delays[rcvrs[i+1]] = [delay]
            print "per-reciever statistics"
            print "rcvr,\t mean delay [ns],\t rms delay [ns]"
            for rcvr in rcvr_delays:
                print "%d,\t %3.2f, \t %3.2f"%(rcvr,n.mean(rcvr_delays[rcvr]),n.std(rcvr_delays[rcvr]))
    
        #axvline(x=476,ls=':',c='gray')

figure(phsfig.number)
subplots_adjust(hspace=0,wspace=0,left=0.08,bottom=0.06)
figtext(0.5,0.05,'chan')
figtext(0.05,0.5,'phase [r]',rotation='vertical')
savefig(calsave[:-4]+'_phs.png')
figure(ampfig.number)
subplots_adjust(hspace=0,wspace=0,left=0.08,bottom=0.09)
figtext(0.5,0.05,'chan')
figtext(0.05,0.35,'amp [dB]',rotation='vertical')
savefig(calsave[:-4]+'_amp.png')
figure(flagfig.number)
subplots_adjust(hspace=0,wspace=0,left=0.08,bottom=0.09)
figtext(0.5,0.05,'chan')
figtext(0.05,0.35,'amp [dB]',rotation='vertical')
savefig(calsave[:-4]+'_flag.png')

figure(figsize=figsize)
for pol in range(M.shape[0]):
    plot(freqs,n.mean(M[pol,:,:],axis=1)*100,pcol[pol])
xlabel('flag fraction')
ylabel('frequency [MHz]')
savefig(calsave[:-4]+'_avgflag.png')
#ms.close()
