#include "slalib.h"
#include "slamac.h"
void slaAmp ( double ra, double da, double date, double eq,
              double *rm, double *dm )
/*
**  - - - - - - -
**   s l a A m p
**  - - - - - - -
**
**  Convert star RA,Dec from geocentric apparent to mean place.
**
**  The mean coordinate system is the post IAU 1976 system,
**  loosely called FK5.
**
**  Given:
**     ra,da     double    apparent RA,Dec (radians)
**     date      double    TDB for apparent place (JD-2400000.5)
**     eq        double    equinox:  Julian epoch of mean place
**
**  Returned:
**     rm,dm     double*   mean RA,Dec (radians)
**
**  References:
**     1984 Astronomical Almanac, pp B39-B41.
**     (also Lederle & Schwan, Astron. Astrophys. 134, 1-6, 1984)
**
**  Notes:
**
**  1)  The distinction between the required TDB and TT is always
**      negligible.  Moreover, for all but the most critical
**      applications UTC is adequate.
**
**  2)  Iterative techniques are used for the aberration and light
**      deflection corrections so that the routines slaAmp (or
**      slaAmpqk) and slaMap (or slaMapqk) are accurate inverses;
**      even at the edge of the Sun's disc the discrepancy is only
**      about 1 nanoarcsecond.
**
**  3)  Where multiple apparent places are to be converted to mean
**      places, for a fixed date and equinox, it is more efficient to
**      use the slaMappa routine to compute the required parameters
**      once, followed by one call to slaAmpqk per star.
**
**  4)  The accuracy is sub-milliarcsecond, limited by the
**      precession-nutation model (IAU 1976 precession, Shirai &
**      Fukushima 2001 forced nutation and precession corrections).
**
**  5)  The accuracy is further limited by the routine slaEvp, called
**      by slaMappa, which computes the Earth position and velocity
**      using the methods of Stumpff.  The maximum error is about
**      0.3 mas.
**
**  Called:  slaMappa, slaAmpqk
**
**  Last revision:   26 December 2004
**
**  Copyright P.T.Wallace.  All rights reserved.
**
*/
{
   double amprms[21];    /* Mean-to-apparent parameters */

   slaMappa ( eq, date, amprms );
   slaAmpqk ( ra, da, amprms, rm, dm );
}
