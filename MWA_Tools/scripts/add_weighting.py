# Add the robustness parameter to the fitsheader

import pyfits
import os

def add_weighting(fitsimage,robustness):
   if os.path.exists(fitsimage):
      hdu_in=pyfits.open(fitsimage,mode='update')
      hdr_in=hdu_in[0].header
      hdr_in.update('robust',robustness)
      hdu_in.flush()
   else:
      print fitsimage+' does not exist!'

if __name__ == "__main__":
   str_delays=add_weighting(fitsimage,robustness)

