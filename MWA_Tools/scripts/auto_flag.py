import numpy,re
import os,os.path,sys
import math
import logging
import shutil
from threading import current_thread

import mwapy
import mwapy.get_observation_info
from mwapy.obssched.base import schedule

db=schedule.getdb()

###########################################

# A CASA-based auto-flagging script
# for the 32-tile commissioning subarrays
# Currently, set vis=<filename.ms>
# And then execfile the script
# Would be nice to add support for 32T data

############################################

try:
    print "Auto-flagging %s"%vis
    if not os.path.exists(vis):
        print "%s does not exist"%vis
    else:
        print "flagDC"
        flagDC(vis)
        print "flagChanGaps"
        flagChanGaps(vis)

# Currently have to remove the first four seconds
        print "Quack"
        tflagdata(vis=vis,mode='quack',quackinterval=4,quackmode='beg')

# Get observation number directly from the measurement set
        tb.open(vis+'/OBSERVATION')
        obsnum=int(tb.getcol('MWA_GPS_TIME'))
        tb.close

        print "found obsnum = ",obsnum
# Could expand this call to get the right flagging tables from the database
#info=mwapy.get_observation_info.MWA_Observation(obsnum,db=db)

    	if (obsnum>1030000000) and (obsnum<=1032653528):
    	    print 'Applying Alpha flags.'
    	    tflagdata(vis=vis,mode='manual',antenna='Tile025') #Sings
    	    tflagdata(vis=vis,mode='manual',antenna='Tile035') #Sings
    	if (obsnum>1032700488) and (obsnum<=1034927848):
    	    print 'Applying Beta flags.'
    	    tflagdata(vis=vis,mode='manual',antenna='Tile015') #Sings
    	    tflagdata(vis=vis,mode='manual',antenna='Tile051') #Sings
    	    tflagdata(vis=vis,mode='manual',antenna='Tile081') #Sings
    	    tflagdata(vis=vis,mode='manual',antenna='Tile085') #Sings
    	    tflagdata(vis=vis,mode='manual',antenna='Tile053') #Bad pointing
            tflagdata(vis=vis,mode='manual',antenna='Tile088') #bad amplitude
    	if (obsnum>1034928064) and (obsnum<=1037011960):
    	    print 'Applying Gamma flags.'
    	    tflagdata(vis=vis,mode='manual',antenna='Tile071') #Sings
    	    tflagdata(vis=vis,mode='manual',antenna='Tile101') #Dead RF
    	    tflagdata(vis=vis,mode='manual',antenna='Tile105') #Dead RF
    	if (obsnum>1037011970) and (obsnum<=1037262456):
    	    print 'Applying Delta flags.'
    	    tflagdata(vis=vis,mode='manual',antenna='Tile111') #Sings
    	    tflagdata(vis=vis,mode='manual',antenna='Tile118') #Bad pointing
    	    tflagdata(vis=vis,mode='manual',antenna='Tile138') #Bad pointing
    	    tflagdata(vis=vis,mode='manual',antenna='Tile154') #Bad pointing
    	    tflagdata(vis=vis,mode='manual',antenna='Tile153',correlation='XX') # Dead RF
    	if (obsnum>1037262460) and (obsnum<=1038118344):
    	    print 'Applying Epsilon flags.'
    	    tflagdata(vis=vis,mode='manual',antenna='Tile138') #Bad pointing
    	    tflagdata(vis=vis,mode='manual',antenna='Tile154') #Bad pointing
    	    tflagdata(vis=vis,mode='manual',antenna='Tile153',correlation='XX') # Dead RF
    	if (obsnum>1038118344) and (obsnum<=1039320536):
    	    print 'Applying Zeta flags.'
    	    tflagdata(vis=vis,mode='manual',antenna='Tile071') #High noise - extra power
    	    tflagdata(vis=vis,mode='manual',antenna='Tile077') #Suspicious
    	    tflagdata(vis=vis,mode='manual',antenna='Tile101') #Dead RF
    	    tflagdata(vis=vis,mode='manual',antenna='Tile111') #Sings
    	if (obsnum>1039320536):
    	    print 'Applying Eta flags.'
    	    tflagdata(vis=vis,mode='manual',antenna='Tile035') #Sings
    	    tflagdata(vis=vis,mode='manual',antenna='Tile045') #Digital oddities
    	    tflagdata(vis=vis,mode='manual',antenna='Tile068') #Digital oddities
    
#Orbcomm
    	tflagdata(vis=vis,mode='manual',spw='0:136MHz~138.5MHz')
# Some CASA auto-flagging, probably needs tweaking
    	testautoflag(vis=vis, ntime=10, extendflags=false,timecutoff=4.0, freqcutoff=3.0, usepreflags=True, datacolumn='data', writeflags=True)
    	flagautocorr(vis)
    	tflagdata(vis=vis,mode='tfcrop')
        flagmanager(vis=vis,mode='save',versionname='MWAflag')

except:
    print 'You need to set vis using, e.g. vis="1023456789.ms" before executing this script.' 
    raise 
