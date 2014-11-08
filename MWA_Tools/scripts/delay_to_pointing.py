import getopt,sys,os,logging,shutil,datetime,re,subprocess,math,tempfile,string,glob
import ephem
import pyfits
from mwapy import ephem_utils
import numpy
from delay_to_pointing import *

######################################################################
def main():

    datetime=None
    delays_tomatch=[]
    try:
        opts, args = getopt.getopt(sys.argv[1:], 
                                   "h",
                                   ["help",
                                    "datetime=",
                                    "delays="]
                                   )
    except getopt.GetoptError,err:
        sys.stderr.write('Unable to parse command-line options: %s\n',err)
        usage()
        sys.exit(2)

    for opt,val in opts:
        # Usage info only
        if opt in ("-h", "--help"):
            usage()
            sys.exit(1)
        elif opt in ("--datetime"):
            datetime=val
        elif opt in ("--delays"):
            try:
                if (',' in val):
                    delays_tomatch=map(int,val.split(','))
                else:
                    delays_tomatch=16*[int(val)]
            except:
                sys.stderr.write("Could not parse beamformer delays %s\n" % val)
                sys.exit(1)

    if datetime is None:
       sys.stderr.write('Must give a datetime string with the form YYYYMMDDhhmmss')
       sys.exit(1)
    if (delays_tomatch is None or len(delays_tomatch)<16):
       sys.stderr.write('Must supply a set of 16 beamformer delays')
       sys.exit(1)


    # get the list of pointing delay positions
    dir=os.path.dirname(__file__)
    if (len(dir)==0):
        dir='.'
    grid_database=dir + '/' + 'grid_points.dat'

    if not os.path.exists(grid_database):
        sys.stderr.write('Cannot open grid database %s' % grid_database)
        sys.exit(2)
    f=open(grid_database,'r')
    lines=f.readlines()
    grid_pointings=[]
    for line in lines:
        if (line.startswith('#')):
            continue
        d=line.split('|')
        s=d[-1]
        delays=[int(x) for x in (s.replace('{','').replace('}','')).split(',')]
        name=d[0] + d[1]
        grid_pointings.append(gridPointing(name, float(d[2]), float(d[3]), delays))

    for grid_pointing in grid_pointings:
        if (grid_pointing.delays == delays_tomatch):
            try:
                ra,dec=grid_pointing.radec(datetime)
            except:
                sys.stderr.write('Unable to determine RA,Dec from pointing information')
                sys.exit(1)
            print "Delay=%s at %s: (Az,El)=(%.5f, %.5f), (RA,Dec)=(%.5f, %.5f)" % (delays_tomatch,datetime,grid_pointing.az,grid_pointing.el,ra,dec)
            return
    print "Did not find a matching delay pointing for %s" % delays_tomatch


# Running as executable
if __name__=='__main__':
    main()
