import os,numpy
from taskinit import *
from casa import flagdata
def flagDC(vis):
    ms.open(vis)
    rec = ms.getdata(['axis_info'])
    df = rec['axis_info']['freq_axis']['resolution'][len(rec['axis_info']['freq_axis']['resolution'])/2]/10000
    ms.close()
    chans=numpy.array(range(24))*(128/df)+(64/df)
    spw=','.join(["0:%s"%ch for ch in chans])
    flagdata(vis=vis,flagbackup=True,mode='manualflag',spw=spw)
