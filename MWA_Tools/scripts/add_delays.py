# Add the delays to the fitsheader of an existing fits file

import pyfits
import os

def add_delays(obsnum,fitsimage):
   if os.path.exists(fitsimage):
      metafits=obsnum+'.metafits'

      if os.path.exists(metafits):
         hdu_in=pyfits.open(metafits)
         str_delays=hdu_in[0].header['DELAYS']
         hdu_in.flush()
      else:
         try:
            import mwapy.get_observation_info
            from mwapy.obssched.base import schedule
            db=schedule.getdb()
         except:
            print 'Unable to open connection to database'
            raise KeyboardInterrupt
         info=mwapy.get_observation_info.MWA_Observation(obsnum,db=db)
         delays=info.delays 
         str_delays=','.join(map(str,delays)) 
         db.close()
         schedule.tempdb.close()

      hdu_in=pyfits.open(fitsimage,mode='update')
      hdr_in=hdu_in[0].header
      hdr_in.update('delays',str_delays)
      hdu_in.flush()

      return str_delays
   else:
      print fitsimage+' does not exist!'

if __name__ == "__main__":
   str_delays=add_delays(obsnum,fitsimage)

