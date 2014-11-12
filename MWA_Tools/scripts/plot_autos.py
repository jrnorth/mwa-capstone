#little script to plot auto spectra
#DCJ 14 Dec 2011
#set vis = 'filename.ms'
#and datacol = 'data' or 
# datacol = 'corrected_data'

from pylab import *
import numpy as n

try:
    print datacol
except:
    datacol = 'data'

calsave = vis[:-3]+'.cal.npz'
try:
    F = n.load(calsave)
    G = F['G']
except(IOError):
    print calsave,"not found"
    G = None
ms.open(vis)
rec = ms.getdata(['axis_info'])
freqs = rec['axis_info']['freq_axis']['chan_freq']/1e6
ms.selectinit()
ms.select({'uvdist':[0,0.01]})
ms.selectpolarization(['xx'])
rec = ms.getdata([datacol,'flag','antenna1','antenna2'],ifraxis=True)
D = n.ma.masked_where(rec['flag'].squeeze(),rec[datacol].squeeze())
if n.mean(rec['flag'])>0.9:
    D = n.ma.array(rec[datacol].squeeze())
print D.shape
print D.min(),D.max()
D = n.mean(D,axis=2)
if G is not None: D /= G
#D = n.ma.array(rec['data'].squeeze())
figure()
clf()
for i in range(D.shape[1]):
    ax = subplot(6,6,i+1);
    plot(freqs,n.ma.abs(D[:,i].filled(n.nan)),'.k',ms=2)
    if (i % 6):yticks([]);ylabel('')
    if (D.shape[1]-6)>i: xticks([]);xlabel('')
    else: xticks(freqs[range(freqs.size/4,freqs.size,freqs.size/3)].astype(int).squeeze().tolist())
    print D[D>0].shape
    ylim([n.ma.abs(D[D>0]).min()*0.8,n.ma.abs(D).max()*1.1])
    xlim([freqs.min(),freqs.max()])
    text(0.8,0.8,str(i+1),transform=ax.transAxes)
subplots_adjust(hspace=0,wspace=0,left=0.08,bottom=0.09)
figtext(0.5,0.05,'MHz')
ms.close()
