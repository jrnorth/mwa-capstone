import os
from taskinit import *
from casa import flagdata
import numpy

def flagChanGaps(vis,width):
    ms.open(vis)
    rec = ms.getdata(['axis_info'])
    df = rec['axis_info']['freq_axis']['resolution'][len(rec['axis_info']['freq_axis']['resolution'])/2]/10000
    ms.close()

    bchan=numpy.array(range(24))*(128/df)
    echan=bchan+width
    spl=[]
    for i in range(24):
        spl.append("0:%s~%s"%(bchan[i],echan[i]))
    
    spw=','.join(spl)
    flagdata(vis=vis,flagbackup=True,mode='manualflag',spw=spw)

    bchan=numpy.array(range(24))*(128/df)+(128/df)-width-1
    echan=bchan+width
    spl=[]
    for i in range(24):
        spl.append("0:%s~%s"%(bchan[i],echan[i]))

    spw=','.join(spl)
    flagdata(vis=vis,flagbackup=True,mode='manualflag',spw=spw)
